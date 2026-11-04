"""Клавиатура и буфер обмена: сочетания клавиш, печать текста, вставка через Ctrl+V."""
import ctypes
import re
import time
from ctypes import wintypes

u = ctypes.windll.user32
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x0002, 0x0004


# ---------------- клавиши ----------------

VK = {"win": 0x5B, "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "tab": 0x09, "enter": 0x0D, "esc": 0x1B,
      "space": 0x20, "backspace": 0x08, "delete": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23,
      "pageup": 0x21, "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
      "printscreen": 0x2C, "capslock": 0x14, "menu": 0x5D}
EXTENDED = {"win", "delete", "insert", "home", "end", "pageup", "pagedown", "left", "up", "right", "down", "menu"}


def send_keys(keys):
    """Зажимает клавиши по порядку и отпускает в обратном — так работают сочетания вроде Win+Tab."""
    u = ctypes.windll.user32
    codes = []
    for k in keys:
        if k in VK:
            code = VK[k]
        elif re.fullmatch(r"f\d{1,2}", k) and 1 <= int(k[1:]) <= 12:
            code = 0x6F + int(k[1:])
        else:
            code = ord(k.upper())
        codes.append((code, 1 if k in EXTENDED else 0))
    for code, ext in codes:
        u.keybd_event(code, 0, ext, 0)
        time.sleep(0.02)
    for code, ext in reversed(codes):
        u.keybd_event(code, 0, ext | 2, 0)  # 2 = KEYEVENTF_KEYUP
        time.sleep(0.02)

# ---------------- ввод текста ----------------

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def type_text(text, delay=0.012):
    """Печатает любой текст (в т.ч. русский) в активное окно — независимо от раскладки клавиатуры."""
    for ch in text:
        if ch == "\n":
            ch = "\r"
        for unit in ch.encode("utf-16-le").decode("utf-16-le"):
            code = ord(unit)
            down = INPUT(type=1, u=_INPUTUNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0)))
            up = INPUT(type=1, u=_INPUTUNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))
            arr = (INPUT * 2)(down, up)
            u.SendInput(2, arr, ctypes.sizeof(INPUT))
        time.sleep(delay)


MESSENGERS = {"telegram.exe", "discord.exe", "whatsapp.exe", "viber.exe"}


def foreground_process():
    import psutil
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(u.GetForegroundWindow(), ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).name().lower()
    except Exception:
        return ""


def input_text(text):
    """Ввести текст в активное окно: в мессенджерах — вставкой (там посимвольная печать теряет буквы),
    в остальных программах — печатью."""
    if foreground_process() in MESSENGERS:
        paste_text(text)
    else:
        type_text(text)


def set_clipboard(text):
    """Положить текст в буфер обмена."""
    k = ctypes.windll.kernel32
    k.GlobalAlloc.restype = ctypes.c_void_p
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = [ctypes.c_void_p]
    k.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    data = text.encode("utf-16-le") + b"\x00\x00"
    for _ in range(5):
        if u.OpenClipboard(0):
            break
        time.sleep(0.05)
    else:
        return False
    try:
        u.EmptyClipboard()
        h = k.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
        p = k.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        k.GlobalUnlock(h)
        u.SetClipboardData(13, h)  # CF_UNICODETEXT
        return True
    finally:
        u.CloseClipboard()


def paste_text(text):
    """Вставить текст через буфер обмена (Ctrl+V) и вернуть буферу прежнее содержимое.
    Надёжнее посимвольной печати в программах вроде Telegram, где отдельные символы могут потеряться."""
    old = _clipboard_text()
    if not set_clipboard(text):
        type_text(text, delay=0.05)
        return
    time.sleep(0.05)
    send_keys(["ctrl", "v"])
    time.sleep(0.7)  # программа может обработать вставку не сразу — возвращаем буфер только после
    if old:
        set_clipboard(old)


# ---------------- запасной путь для YouTube в браузере ----------------

def _clipboard_text():
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    k.GlobalLock.restype = ctypes.c_void_p
    u.GetClipboardData.restype = ctypes.c_void_p
    if not u.OpenClipboard(0):
        return ""
    try:
        h = u.GetClipboardData(13)  # CF_UNICODETEXT
        if not h:
            return ""
        p = k.GlobalLock(ctypes.c_void_p(h))
        try:
            return ctypes.wstring_at(p) if p else ""
        finally:
            k.GlobalUnlock(ctypes.c_void_p(h))
    finally:
        u.CloseClipboard()
