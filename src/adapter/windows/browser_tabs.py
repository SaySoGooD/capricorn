"""Адресная строка браузера через UI Automation: прочитать адрес, открыть ссылку в текущей вкладке."""
import logging
import re
import time
import urllib.parse

from src.adapter.windows import window_automation
from src.adapter.windows.keyboard import send_keys, type_text

log = logging.getLogger("capri")


def _urlbar(hwnd):
    """Адресная строка браузера как элемент UI Automation (или None) и её ValuePattern."""
    import comtypes.client
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as UIA
    uia = comtypes.client.CreateObject(UIA.CUIAutomation, interface=UIA.IUIAutomation)
    root = uia.ElementFromHandle(hwnd)
    bar = root.FindFirst(UIA.TreeScope_Descendants,  # Firefox
                         uia.CreatePropertyCondition(UIA.UIA_AutomationIdPropertyId, "urlbar-input"))
    candidates = [bar] if bar else []
    if not candidates:  # Chrome, Edge, Яндекс: поле ввода, в котором записан адрес
        edits = root.FindAll(UIA.TreeScope_Descendants,
                             uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_EditControlTypeId))
        candidates = [edits.GetElement(i) for i in range(min(edits.Length, 8))]
    for el in candidates:
        try:
            vp = el.GetCurrentPattern(UIA.UIA_ValuePatternId).QueryInterface(UIA.IUIAutomationValuePattern)
        except Exception:
            continue
        value = vp.CurrentValue or ""
        if bar is not None or re.search(r"\.\w{2,}(/|$)", value):
            return el, vp
    return None, None


def page_url(hwnd):
    """Адрес любой открытой вкладки браузера (для «запомни этот сайт») или None."""
    try:
        _, vp = _urlbar(hwnd)
        value = ((vp.CurrentValue or "") if vp else "").strip()
    except Exception:
        log.exception("Не удалось прочитать адрес вкладки")
        return None
    if not re.match(r"^(https?://)?[\w\-]+(\.[\w\-]+)*\.[a-zа-я]{2,}(:\d+)?(/\S*)?$", value, re.IGNORECASE):
        return None
    return value if value.startswith("http") else "https://" + value


def browser_url(hwnd):
    """Адрес активной вкладки браузера — читаем адресную строку через UI Automation (без копирования)."""
    try:
        _, vp = _urlbar(hwnd)
        value = (vp.CurrentValue or "") if vp else ""
        if "youtube" in value or "youtu.be" in value:
            return value if value.startswith("http") else "https://" + value
    except Exception:
        log.exception("Не удалось прочитать адрес вкладки")
    return None


def navigate(hwnd, url):
    """Открыть адрес в текущей вкладке браузера. Фокус ставится в адресную строку через UI Automation,
    и Enter нажимается только если там ровно нужный адрес — иначе ничего не жмём (чтобы буквы и цифры
    не ушли в страницу, где на YouTube это горячие клавиши)."""
    try:
        el, vp = _urlbar(hwnd)
        if not el:
            return False
        el.SetFocus()
        time.sleep(0.25)
        if not el.CurrentHasKeyboardFocus:
            send_keys(["ctrl", "l"])  # запасной способ
            time.sleep(0.4)
            if not el.CurrentHasKeyboardFocus:
                log.info("Адресная строка не получила фокус — ничего не печатаю")
                return False
        send_keys(["ctrl", "a"])
        time.sleep(0.1)
        type_text(url)
        time.sleep(0.25)
        typed = (vp.CurrentValue or "").strip()
        if typed.rstrip("/") != url.rstrip("/") and typed.rstrip("/") != url.split("://", 1)[-1].rstrip("/"):
            log.info("В адресной строке не то, что нужно (%r) — не открываю", typed[:120])
            send_keys(["esc"])
            return False
        send_keys(["enter"])
        return True
    except Exception:
        log.exception("Не удалось открыть адрес")
        return False


def youtube_url_seek(seconds):
    """Перематывает видео YouTube: открывает ту же ссылку, где метка времени t заменена на нужную."""
    hwnd = window_automation.find_window(("youtube",))
    if not hwnd or not window_automation.focus(hwnd):
        return False
    url = browser_url(hwnd)
    if not url:
        return False
    parts = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parts.query)
    if "youtu.be" in parts.netloc:  # короткая ссылка youtu.be/ID
        query.setdefault("v", [parts.path.strip("/")])
    if not query.get("v"):
        return False  # это не страница видео (главная, поиск)
    query.pop("t", None)  # старая метка: если оставить, YouTube возьмёт её, а не новую
    keep = {k: v[0] for k, v in query.items() if k in ("v", "list", "index")}
    new = "https://www.youtube.com/watch?" + urllib.parse.urlencode(keep) + f"&t={int(seconds)}s"
    log.info("YouTube: %s → %s", url, new)
    return navigate(hwnd, new)
