"""Клик по элементам окна через UI Automation: найти кнопку/ссылку/пункт меню по названию и нажать.

Тот же механизм, что уже читает адресную строку браузера (browser_tabs), — COM-объект CUIAutomation.
COM в рабочем потоке поднимает ComThreadSetupAdapter, поэтому здесь только обращения к дереву элементов."""
import ctypes
import logging
import time

log = logging.getLogger("capri")

# какие элементы вообще имеет смысл «нажимать» — так обходим не весь огромный DOM, а только кликабельное
CLICKABLE_TYPES = ("UIA_ButtonControlTypeId", "UIA_HyperlinkControlTypeId", "UIA_MenuItemControlTypeId",
                   "UIA_TabItemControlTypeId", "UIA_ListItemControlTypeId", "UIA_CheckBoxControlTypeId",
                   "UIA_RadioButtonControlTypeId", "UIA_SplitButtonControlTypeId")
# паттерны «нажатия» по приоритету: (id паттерна, интерфейс, метод без аргументов)
INVOKERS = (("UIA_InvokePatternId", "IUIAutomationInvokePattern", "Invoke"),
            ("UIA_TogglePatternId", "IUIAutomationTogglePattern", "Toggle"),
            ("UIA_SelectionItemPatternId", "IUIAutomationSelectionItemPattern", "Select"),
            ("UIA_ExpandCollapsePatternId", "IUIAutomationExpandCollapsePattern", "Expand"))


def _uia():
    """COM-объект UI Automation и сгенерированный модуль с константами."""
    import comtypes.client
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as UIA
    return comtypes.client.CreateObject(UIA.CUIAutomation, interface=UIA.IUIAutomation), UIA


def _clickable_condition(uia, UIA):
    """Условие «это один из кликабельных типов». None — если константы недоступны (обойдём всё дерево)."""
    conds = []
    for name in CLICKABLE_TYPES:
        tid = getattr(UIA, name, None)
        if tid is not None:
            conds.append(uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, tid))
    if not conds:
        return None
    cond = conds[0]
    for extra in conds[1:]:
        cond = uia.CreateOrCondition(cond, extra)
    return cond


def _press(uia, UIA, el) -> bool:
    """Нажать элемент: сперва «родным» паттерном (Invoke/Toggle/Select), иначе — кликом мышью по центру."""
    for pat_name, iface_name, method in INVOKERS:
        pid, iface = getattr(UIA, pat_name, None), getattr(UIA, iface_name, None)
        if pid is None or iface is None:
            continue
        try:
            pattern = el.GetCurrentPattern(pid)
            if not pattern:
                continue
            getattr(pattern.QueryInterface(iface), method)()
            return True
        except Exception:
            continue
    # запасной способ — клик мышью по центру элемента
    try:
        r = el.CurrentBoundingRectangle
        if r.right <= r.left or r.bottom <= r.top:
            return False
        x, y = (r.left + r.right) // 2, (r.top + r.bottom) // 2
        u = ctypes.windll.user32
        u.SetCursorPos(int(x), int(y))
        time.sleep(0.05)
        u.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
        u.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
        return True
    except Exception:
        log.exception("Клик мышью по элементу не удался")
        return False


def click(name: str, hwnd: int | None = None) -> bool:
    """Найти в окне кликабельный элемент, чьё название совпадает (или содержит) с name, и нажать."""
    needle = (name or "").strip().casefold()
    if not needle:
        return False
    hwnd = hwnd or ctypes.windll.user32.GetForegroundWindow()
    try:
        uia, UIA = _uia()
        root = uia.ElementFromHandle(hwnd)
    except Exception:
        log.exception("UI Automation недоступен")
        return False
    cond = _clickable_condition(uia, UIA) or uia.CreateTrueCondition()
    try:
        found = root.FindAll(UIA.TreeScope_Descendants, cond)
    except Exception:
        log.exception("Не удалось обойти элементы окна")
        return False
    exact = partial = None
    for i in range(found.Length):
        el = found.GetElement(i)
        try:
            nm = (el.CurrentName or "").strip().casefold()
            if not nm or not el.CurrentIsEnabled:
                continue
        except Exception:
            continue
        if nm == needle:
            exact = el
            break
        if partial is None and needle in nm:
            partial = el
    el = exact or partial
    if el is None:
        log.info("Элемент «%s» в окне не найден", name)
        return False
    try:
        el.SetFocus()
        time.sleep(0.05)
    except Exception:
        pass
    ok = _press(uia, UIA, el)
    log.info("Клик по «%s»: %s", name, "ок" if ok else "не вышло")
    return ok
