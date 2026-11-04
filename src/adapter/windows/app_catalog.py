"""Каталог программ: ярлыки «Пуска» и рабочего стола, Get-StartApps и «Программы и компоненты»."""
import difflib
import logging
import os
import re
import subprocess
import threading

from src.adapter.windows.powershell import NO_WINDOW, ps_json
from src.application.assistant.fuzzy import sounds_like
from src.application.assistant.text import norm, translit

log = logging.getLogger("capri")


SKIP_WORDS = ("uninstall", "удален", "удалить", "деинсталл", "readme", "help", "справка", "documentation",
              "license", "support", "поддержк", "feedback", "release notes", "website")


def installed_programs():
    """[(название, путь к exe)] из «Программ и компонентов» Windows: значок программы обычно и есть её exe."""
    import winreg
    out = []
    roots = [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")]
    for hive, path in roots:
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
                name = str(winreg.QueryValueEx(sub, "DisplayName")[0])
            except OSError:
                continue
            values = {}
            for field in ("DisplayIcon", "InstallLocation", "UninstallString"):
                try:
                    values[field] = str(winreg.QueryValueEx(sub, field)[0])
                except OSError:
                    values[field] = ""
            exe = re.sub(r",\s*-?\d+$", "", values["DisplayIcon"]).strip().strip('"')
            base = os.path.basename(exe).lower()
            if exe.lower().endswith(".exe") and "unins" not in base and "setup" not in base and os.path.isfile(exe):
                out.append((norm(name), exe))
                continue
            # значок — деинсталлятор (так у Steam): ищем рядом exe с названием программы, steam → steam.exe
            folder = values["InstallLocation"].strip().strip('"')
            if not os.path.isdir(folder):
                m = re.match(r'^"?([^"]+?\.exe)', values["UninstallString"] or exe)
                folder = os.path.dirname(m.group(1)) if m else ""
            guess = os.path.join(folder, re.sub(r"[^\w\-]", "", name) + ".exe") if folder else ""
            if guess and os.path.isfile(guess):
                out.append((norm(name), guess))
    return out


class AppIndex:
    def __init__(self):
        self.items = {}
        self.lock = threading.Lock()
        self.ready = threading.Event()

    def build(self):
        items = {}
        try:
            for app in ps_json("Get-StartApps | Select-Object Name,AppID"):
                name = norm(app.get("Name") or "")
                if name and not any(w in name for w in SKIP_WORDS):
                    items[name] = ("appid", app.get("AppID"))
        except Exception:
            log.exception("Get-StartApps")
        home = os.path.expanduser("~")
        dirs = [os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
                os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
                os.path.join(home, "Desktop"), os.path.join(home, "OneDrive", "Desktop"),
                os.path.join(os.environ.get("PUBLIC", ""), "Desktop")]
        for d in dirs:
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".lnk", ".url", ".appref-ms")):
                        name = norm(os.path.splitext(f)[0])
                        # ярлык надёжнее идентификатора из Get-StartApps: у программ вроде Discord
                        # (установщик Squirrel) запуск по идентификатору ничего не открывает
                        if (name and not any(w in name for w in SKIP_WORDS)
                                and items.get(name, ("appid",))[0] != "file"):
                            items[name] = ("file", os.path.join(root, f))
        # установленные программы из реестра — на случай, если ярлыка в «Пуске» нет (бывает у Steam)
        for name, exe in installed_programs():
            if name not in items and not any(w in name for w in SKIP_WORDS):
                items[name] = ("file", exe)
        with self.lock:
            self.items = items
        self.ready.set()
        log.info("Найдено приложений: %d", len(items))

    def candidates(self, query, aliases, limit=4):
        """Подходящие приложения, лучшие первыми: [(оценка, название, цель)]."""
        q = norm(query)
        variants = {q, translit(q)}
        if q in aliases:
            variants.add(norm(aliases[q]))
        with self.lock:
            items = list(self.items.items())
        scored = {}
        for name, target in items:
            best = 0.0
            for v in variants:
                if v == name:
                    score = 1.0
                elif len(v) >= 3 and re.search(r"(^|\s)" + re.escape(v), name):
                    score = 0.93 - 0.003 * len(name)
                else:
                    score = difflib.SequenceMatcher(None, v, name).ratio()
                    first = name.split()[0] if name.split() else name
                    if sounds_like(v, name):
                        score = max(score, 0.97)  # звучит как всё название: «роблокс» = «roblox»
                    elif sounds_like(v, first):
                        score = max(score, 0.86)  # звучит так же: «клод/cloud» ~ «claude»
                best = max(best, score)
            if best >= 0.72 and best > scored.get(name, (0,))[0]:
                scored[name] = (best, target)
        ranked = sorted(((s, n, t) for n, (s, t) in scored.items()), key=lambda x: -x[0])
        return ranked[:limit]

    def find(self, query, aliases):
        found = self.candidates(query, aliases, 1)
        return (found[0][1], found[0][2]) if found else None

    @staticmethod
    def launch(target):
        kind, value = target
        if kind == "appid":
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{value}"], creationflags=NO_WINDOW)
            return
        os.startfile(value)

    def launch_best(self, query, options):
        """Запустить лучший вариант; если Windows его не открыла (например, Roblox.lnk — «операция
        отменена»), пробуем похожие ярлыки с тем же началом (Roblox Player), а в конце — через проводник,
        как при двойном клике. options: [(оценка, имя, цель)]. Возвращает имя запущенного или None."""
        first = options[0]
        q = first[1].split()[0] if first[1].split() else ""  # «roblox» из найденного «roblox», а не «роблокс»
        with self.lock:
            similar = [(1.0, n, t) for n, t in self.items.items() if n != first[1] and q and n.startswith(q)
                       and not re.search(r"studio|uninstall|update", n)]
        for _, name, target in [first] + sorted(similar, key=lambda x: len(x[1])):
            try:
                self.launch(target)
                return name
            except OSError as e:
                log.info("%s не запустился (%s)", name, e)
        if first[2][0] == "file":
            subprocess.Popen(["explorer.exe", first[2][1]], creationflags=NO_WINDOW)
            return first[1]
        return None
