"""Браузер Капри через Chrome DevTools Protocol.

Запускаем НАСТОЯЩИЙ установленный Chrome со своим отдельным профилем (user-data-dir) и портом отладки,
без `--headless` и без флагов автоматизации. При таком запуске navigator.webdriver остаётся false, нет
инфобара «управляется автоматизацией» и нет cdc-переменных Selenium — для антибота это обычный браузер.
Управление идёт по CDP через веб-сокет страницы (библиотека websocket-client, подключается лениво).

Firefox сюда не подходит: он не говорит на CDP (у него свой протокол WebDriver BiDi)."""
import json
import logging
import os
import subprocess
import time
import urllib.request

from src.application.assistant.interfaces.i_browser_automation_adapter import IBrowserAutomationAdapter

log = logging.getLogger("capri")

NO_WINDOW = 0x08000000
DETACHED = 0x00000008

CHROME_PATHS = (
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
)


class CdpBrowserAdapter(IBrowserAutomationAdapter):
    def __init__(self, settings: dict, base_dir: str) -> None:
        self._port = int(settings.get("browser_cdp_port", 9222))
        self._exe = str(settings.get("browser_exe") or "").strip()
        profile = str(settings.get("browser_profile_dir") or "").strip()
        default_profile = os.path.join(os.environ.get("LOCALAPPDATA", base_dir), "Capri", "browser")
        self._profile = profile or default_profile
        self._pidfile = os.path.join(self._profile, "capri_browser.pid")
        self._ws = None
        self._id = 0

    # ---------- запуск / связь ----------
    def _find_chrome(self) -> str | None:
        if self._exe and os.path.isfile(self._exe):
            return self._exe
        for raw in CHROME_PATHS:
            path = os.path.expandvars(raw)
            if os.path.isfile(path):
                return path
        return None

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % self._port, timeout=1.5):
                return True
        except Exception:
            return False

    def launch(self, timeout: float = 30.0) -> bool:
        if self.available:
            return True
        exe = self._find_chrome()
        if not exe:
            log.info("Браузер Капри: не нашла chrome.exe/msedge.exe — задай browser_exe в настройках")
            return False
        os.makedirs(self._profile, exist_ok=True)
        args = [exe, "--remote-debugging-port=%d" % self._port, "--user-data-dir=%s" % self._profile,
                "--no-first-run", "--no-default-browser-check", "--start-maximized", "about:blank"]
        try:
            proc = subprocess.Popen(args, creationflags=NO_WINDOW | DETACHED,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(self._pidfile, "w", encoding="utf-8") as fh:
                fh.write(str(proc.pid))
        except Exception as e:
            log.warning("Браузер Капри: не запустился: %s", e)
            return False
        log.info("Браузер Капри: запускаю %s (профиль %s, порт %d)", os.path.basename(exe), self._profile, self._port)
        end = time.time() + timeout
        while time.time() < end:
            if self.available:
                return True
            time.sleep(0.4)
        log.info("Браузер Капри: отладочный порт так и не ответил за %.0f с", timeout)
        return False

    def _connect(self) -> bool:
        """Подключиться к веб-сокету открытой вкладки (создаём её, если надо)."""
        if self._ws is not None:
            return True
        try:
            raw = urllib.request.urlopen("http://127.0.0.1:%d/json" % self._port, timeout=3).read()
            targets = json.loads(raw)
        except Exception as e:
            log.info("Браузер Капри: список вкладок недоступен: %s", e)
            return False
        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        if not pages:
            try:  # вкладок нет — просим браузер создать новую
                urllib.request.urlopen("http://127.0.0.1:%d/json/new?about:blank" % self._port, timeout=3).read()
                targets = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json" % self._port, timeout=3).read())
                pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            except Exception as e:
                log.info("Браузер Капри: не удалось создать вкладку: %s", e)
                return False
        if not pages:
            return False
        try:
            import websocket
            self._ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=20,
                                                   max_size=None, enable_multithread=True)
            self._rpc("Page.enable")
            self._rpc("Runtime.enable")
            return True
        except Exception as e:
            log.info("Браузер Капри: не подключилась к вкладке (websocket-client установлен?): %s", e)
            self._ws = None
            return False

    def _rpc(self, method: str, params: dict | None = None, timeout: float = 20.0):
        self._id += 1
        mid = self._id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            self._ws.settimeout(max(0.1, end - time.time()))
            try:
                msg = json.loads(self._ws.recv())
            except Exception:
                break
            if msg.get("id") == mid:  # ответы событий (без id) пропускаем
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result")
        raise TimeoutError(method)

    def _eval(self, expr: str, timeout: float = 20.0):
        r = self._rpc("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, timeout)
        return (r or {}).get("result", {}).get("value")

    def _wait_ready(self, timeout: float = 25.0) -> None:
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self._eval("document.readyState", timeout=5) == "complete":
                    return
            except Exception:
                return
            time.sleep(0.3)

    # ---------- действия ----------
    def open(self, url: str) -> bool:
        if not url.startswith(("http://", "https://", "about:", "file:")):
            url = "https://" + url
        if not self.available and not self.launch():
            return False
        if not self._connect():
            return False
        try:
            self._rpc("Page.navigate", {"url": url})
            self._wait_ready()
            return True
        except Exception as e:
            log.info("Браузер Капри: не открыла %s: %s", url, e)
            return False

    def page_text(self, limit: int = 8000) -> str | None:
        if not self._connect():
            return None
        try:
            txt = self._eval("document.body ? document.body.innerText : ''")
        except Exception as e:
            log.info("Браузер Капри: не прочитала страницу: %s", e)
            return None
        if not txt:
            return None
        return " ".join(str(txt).split())[:limit]

    def links(self, limit: int = 60) -> list[tuple[str, str]]:
        if not self._connect():
            return []
        expr = ("JSON.stringify([...document.querySelectorAll('a[href]')]"
                ".map(a=>({t:(a.innerText||a.textContent||'').trim(),h:a.href}))"
                ".filter(x=>x.t && x.h).slice(0,%d))" % max(1, limit))
        try:
            data = json.loads(self._eval(expr) or "[]")
        except Exception:
            return []
        return [(d["t"], d["h"]) for d in data]

    def click_link(self, text: str) -> str | None:
        if not self._connect():
            return None
        q = json.dumps(text.lower())
        expr = ("(function(){var q=%s;var el=[...document.querySelectorAll('a[href]')]"
                ".find(a=>((a.innerText||a.textContent||'').toLowerCase().includes(q)));"
                "if(!el)return null;el.scrollIntoView({block:'center'});el.click();return el.href;})()" % q)
        try:
            href = self._eval(expr)
        except Exception as e:
            log.info("Браузер Капри: клик по ссылке не вышел: %s", e)
            return None
        if href:
            self._wait_ready()
        return href

    def current_url(self) -> str | None:
        if not self._connect():
            return None
        try:
            return self._eval("location.href")
        except Exception:
            return None

    def close(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        pid = None
        try:
            with open(self._pidfile, encoding="utf-8") as fh:
                pid = int(fh.read().strip())
        except Exception:
            pid = None
        if pid:
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], creationflags=NO_WINDOW,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            except Exception as e:
                log.info("Браузер Капри: не закрылся по pid %s: %s", pid, e)
        try:
            os.remove(self._pidfile)
        except OSError:
            pass
