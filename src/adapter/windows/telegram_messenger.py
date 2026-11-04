"""Telegram Desktop: открыть чат по имени или номеру в списке."""
import logging
import time

from src.adapter.windows.keyboard import paste_text, send_keys
from src.adapter.windows.window_automation import wait_and_focus, window_title

log = logging.getLogger("capri")


def _telegram_search_field(hwnd):
    """Поле «Поиск» над списком чатов Telegram (через UI Automation) или None."""
    try:
        import comtypes.client
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient as UIA
        uia = comtypes.client.CreateObject(UIA.CUIAutomation, interface=UIA.IUIAutomation)
        edits = uia.ElementFromHandle(hwnd).FindAll(
            UIA.TreeScope_Descendants,
            uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_EditControlTypeId))
        for i in range(edits.Length):
            e = edits.GetElement(i)
            if e.CurrentIsKeyboardFocusable and (e.CurrentName or "").lower() in ("поиск", "search"):
                return e
    except Exception:
        log.exception("Поле поиска Telegram не найдено")
    return None


def telegram_open_chat(index=None, name=None):
    """Открыть чат в Telegram Desktop: по имени (через поле «Поиск») или по номеру в списке.
    Успех проверяем по заголовку окна — у Telegram это название открытого чата."""
    hwnd = wait_and_focus(("telegram",), timeout=8)
    if not hwnd:
        return False
    before = window_title(hwnd)
    field = _telegram_search_field(hwnd)
    if field is not None:
        field.SetFocus()
        time.sleep(0.25)
    else:  # запасной путь: Esc закрывает чат, курсор уходит в поиск
        send_keys(["esc"])
        time.sleep(0.3)
        send_keys(["esc"])
        time.sleep(0.3)
    send_keys(["ctrl", "a"])  # очистить то, что уже было в поиске
    time.sleep(0.1)
    if name:
        paste_text(name)
        time.sleep(1.5)  # Telegram ищет по мере ввода
        send_keys(["enter"])  # первый результат
    else:
        send_keys(["backspace"])
        time.sleep(0.3)
        for _ in range(max(1, index or 1)):
            send_keys(["down"])
            time.sleep(0.1)
        send_keys(["enter"])
    for _ in range(10):
        time.sleep(0.3)
        title = window_title(hwnd).replace("‎", "").lower()
        if name and any(title.startswith(w) or f" {w}" in title for w in name.lower().split()):
            return True
        if not name and title != before.replace("‎", "").lower():
            return True
    log.info("Чат не открылся: заголовок окна «%s»", window_title(hwnd))
    return False
