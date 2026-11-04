"""Окна Windows: поиск по заголовку, фокус, прокрутка, поле поиска, полноэкранные приложения."""
import ctypes
import logging
import os
import time
from ctypes import wintypes

from src.adapter.windows.keyboard import send_keys, type_text

log = logging.getLogger("capri")


u = ctypes.windll.user32


# ---------------- окна ----------------

def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def foreground_title():
    hwnd = u.GetForegroundWindow()
    return window_title(hwnd) if hwnd else ""


def process_window(exe_names):
    """Главное видимое окно процесса (по имени exe). Нужно для программ, у которых заголовок окна —
    не их название: у Telegram Desktop это название открытого чата."""
    import psutil
    exe_names = {n.lower() for n in exe_names}
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if u.IsWindowVisible(hwnd) and window_title(hwnd):
            pid = wintypes.DWORD()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                if psutil.Process(pid.value).name().lower() in exe_names:
                    found.append(hwnd)
            except Exception:
                pass
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None


PROCESS_OF = {"telegram": ("telegram.exe",), "discord": ("discord.exe",), "whatsapp": ("whatsapp.exe",)}


def find_window(keywords):
    for k in keywords:  # у некоторых программ ищем окно по процессу, а не по заголовку
        if k in PROCESS_OF:
            hwnd = process_window(PROCESS_OF[k])
            if hwnd:
                return hwnd
    return _find_by_title(keywords)


def _find_by_title(keywords):
    """Видимое окно, в заголовке которого есть одно из слов. Если подходит активное окно — берём его;
    иначе предпочитаем окно, чей заголовок начинается со слова (сам «Telegram», а не вкладку браузера
    со словом telegram)."""
    fg = u.GetForegroundWindow()
    if fg and any(k in window_title(fg).lower() for k in keywords):
        return fg
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if u.IsWindowVisible(hwnd):
            t = window_title(hwnd).lower()
            if t and any(k in t for k in keywords):
                exact = any(t.startswith(k) for k in keywords)
                found.append((0 if exact else 1, hwnd))
        return True
    u.EnumWindows(cb, 0)
    return min(found, key=lambda x: x[0])[1] if found else None


def is_foreground(hwnd):
    """Активно ли окно hwnd (или его дочернее/владеющее — у браузеров это может быть другое окно того же
    процесса)."""
    fg = u.GetForegroundWindow()
    if not fg:
        return False
    if fg == hwnd or u.GetAncestor(fg, 2) == hwnd:  # GA_ROOT
        return True
    p1, p2 = wintypes.DWORD(), wintypes.DWORD()
    u.GetWindowThreadProcessId(fg, ctypes.byref(p1))
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(p2))
    return p1.value == p2.value and window_title(fg) == window_title(hwnd)


def focus(hwnd):
    """Сделать окно активным. Windows не даёт фоновой программе забирать фокус, поэтому по очереди:
    «пустой» Alt, присоединение к потоку активного окна, а если не вышло — свернуть и развернуть окно.
    Возвращает True, только если окно действительно стало активным."""
    k = ctypes.windll.kernel32
    for attempt in range(3):
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, 9)  # SW_RESTORE
        fg = u.GetForegroundWindow()
        me, fg_tid = k.GetCurrentThreadId(), u.GetWindowThreadProcessId(fg, None)
        attached = bool(fg_tid and fg_tid != me and u.AttachThreadInput(me, fg_tid, True))
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x12, 0, 2, 0)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        if attached:
            u.AttachThreadInput(me, fg_tid, False)
        time.sleep(0.3)
        if is_foreground(hwnd):
            return True
        if attempt == 0:  # SwitchToThisWindow — то, чем пользуется Alt+Tab; часто проходит там, где другое нет
            u.SwitchToThisWindow(hwnd, True)
            time.sleep(0.3)
            if is_foreground(hwnd):
                return True
        if attempt == 1:  # крайний способ: развёрнутое из свёрнутого окно Windows активирует сама
            u.ShowWindow(hwnd, 6)   # SW_MINIMIZE
            time.sleep(0.2)
            u.ShowWindow(hwnd, 9)   # SW_RESTORE
            time.sleep(0.4)
            if is_foreground(hwnd):
                return True
    log.info("Не удалось активировать окно «%s»", window_title(hwnd))
    return False


def wait_and_focus(keywords, timeout=10.0):
    """Ждём, пока появится окно (например, только что запущенный Telegram), и делаем его активным."""
    end = time.time() + timeout
    while time.time() < end:
        hwnd = find_window(keywords)
        if hwnd:
            if is_foreground(hwnd):  # нужное окно уже активно — ничего не переключаем
                return hwnd
            time.sleep(0.6)  # даём окну дорисоваться
            return hwnd if focus(hwnd) else None
        time.sleep(0.4)
    return None


# ---------------- прокрутка ----------------

def _content_point(hwnd):
    """Точка в середине окна, чуть ниже центра — там обычно основное содержимое, а не меню и вкладки."""
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left + r.right) // 2, r.top + int((r.bottom - r.top) * 0.58), r.bottom - r.top


def _own(hwnd):
    """Окно самой Капри (аватар, молния, окна настроек)?"""
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()


def target_window():
    """Окно, которое листать: активное, а если активна сама Капри (по ней кликнули) — следующее под ней."""
    hwnd = u.GetForegroundWindow()
    while hwnd and (_own(hwnd) or not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd)):
        hwnd = u.GetWindow(hwnd, 2)  # GW_HWNDNEXT — следующее окно ниже по z-порядку
    return hwnd


def _visible_point(hwnd):
    """Точка внутри окна, где под курсором именно это окно, а не Капри поверх него (она стоит поверх всех
    окон и может закрывать середину страницы). Колесо мыши получает окно под курсором."""
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    for fx, fy in ((0.5, 0.58), (0.3, 0.58), (0.7, 0.58), (0.5, 0.4), (0.5, 0.75), (0.2, 0.4), (0.8, 0.4),
                   (0.2, 0.75), (0.8, 0.75), (0.35, 0.3), (0.65, 0.3)):
        x, y = r.left + int(w * fx), r.top + int(h * fy)
        under = u.WindowFromPoint(wintypes.POINT(x, y))
        if under and u.GetAncestor(under, 2) == hwnd:  # GA_ROOT — верхнее окно, которому принадлежит точка
            return x, y
    x, y, _ = _content_point(hwnd)
    return x, y


def scroll(notches, hwnd=None, delay=0.012):
    """Крутит колёсико над содержимым активного окна (notches > 0 — вниз). Курсор возвращается на место.
    Колесо, а не клавиши: прокручивает страницу, даже если фокус ввода стоит в каком-нибудь поле."""
    hwnd = hwnd or target_window()
    if not hwnd:
        return False
    x, y = _visible_point(hwnd)
    old = wintypes.POINT()
    u.GetCursorPos(ctypes.byref(old))
    u.SetCursorPos(x, y)
    step = -120 if notches > 0 else 120  # WHEEL_DELTA: «минус» — вниз
    for _ in range(abs(int(notches))):
        u.mouse_event(0x0800, 0, 0, ctypes.c_uint32(step & 0xFFFFFFFF).value, 0)  # MOUSEEVENTF_WHEEL
        time.sleep(delay)
    time.sleep(0.05)
    u.SetCursorPos(old.x, old.y)
    return True


def screen_notches(hwnd=None):
    """Сколько щелчков колеса примерно равно одному экрану (щелчок ≈ 3 строки ≈ 60 px)."""
    hwnd = hwnd or target_window()
    if not hwnd:
        return 8
    _, _, height = _content_point(hwnd)
    return max(3, int(height * 0.8 / 60))


def focus_search(title):
    """Поставить курсор в поиск текущего окна: YouTube — «/», Telegram — Esc, браузер — адресная строка."""
    t = title.lower()
    if "youtube" in t:
        send_keys(["esc"])
        type_text("/")  # «/» на YouTube = фокус в поиск (символом, чтобы не зависеть от раскладки)
        return "youtube"
    if "telegram" in t:
        send_keys(["esc"])
        time.sleep(0.15)
        send_keys(["esc"])
        return "telegram"
    send_keys(["ctrl", "l"])  # адресная строка браузера = поиск
    return "browser"


def window_exe(hwnd):
    """Полный путь к программе, которой принадлежит окно, или None."""
    import psutil
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).exe()
    except Exception:
        return None


def fullscreen_app_active():
    """Открыта игра или видео на весь экран — тогда не лезем со спонтанными репликами."""
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return False
        cls = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(hwnd, cls, 64)
        if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
            return False  # рабочий стол
        r = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        return (r.right - r.left) >= u.GetSystemMetrics(0) and (r.bottom - r.top) >= u.GetSystemMetrics(1)
    except Exception:
        return False
