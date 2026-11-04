"""YouTube в браузере: запуск видео, когда браузер блокирует автозвук, и поиск в текущей вкладке."""
import ctypes
import logging
import time
import urllib.parse

from src.adapter.windows import browser_tabs, window_automation
from src.adapter.windows.audio_endpoint import browser_playing
from src.adapter.windows.keyboard import send_keys

log = logging.getLogger("capri")


def youtube_window():
    """Окно браузера с открытым YouTube (по заголовку активной вкладки)."""
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if u.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            u.GetWindowTextW(hwnd, buf, 512)
            if "youtube" in buf.value.lower():
                found.append(hwnd)
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None


_ensure_token = [0]  # номер последней проверки «заиграло ли видео»; новая команда отменяет старую


def cancel_ensure():
    _ensure_token[0] += 1


def ensure_playing(wait_load=7.0):
    """Браузеры блокируют автозапуск со звуком у вкладок, открытых программой. Ждём звук;
    если тишина — переключаемся на окно YouTube и жмём K (пуск/пауза в плеере), затем проверяем.
    Если за это время пришла новая команда — тихо выходим, чтобы не кликнуть посреди её работы."""
    _ensure_token[0] += 1
    token = _ensure_token[0]
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
    deadline = time.time() + wait_load
    while time.time() < deadline:  # может, запустилось само (или идёт реклама)
        if _ensure_token[0] != token:
            return
        if browser_playing():
            log.info("Видео играет само")
            return
        time.sleep(0.5)
    if _ensure_token[0] != token:
        return
    hwnd = None
    for _ in range(10):  # заголовок вкладки может ещё не смениться на «… - YouTube»
        hwnd = youtube_window()
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        log.info("Окно YouTube не найдено, не нажимаю пуск")
        return
    u = ctypes.windll.user32
    u.keybd_event(0x12, 0, 0, 0)       # «пустой» Alt — без него Windows не даёт сменить активное окно
    u.keybd_event(0x12, 0, 2, 0)
    u.SetForegroundWindow(hwnd)
    time.sleep(0.4)

    # Клик мышью по плееру — настоящее действие пользователя: и окно активирует, и фокус ставит в плеер,
    # и браузер считает это разрешением на звук. Точка (30% ширины, 35% высоты) попадает в плеер
    # и в обычном, и в широком режиме YouTube.
    from ctypes import wintypes
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    x, y = r.left + int((r.right - r.left) * 0.30), r.top + int((r.bottom - r.top) * 0.35)
    old = wintypes.POINT()
    u.GetCursorPos(ctypes.byref(old))
    u.SetCursorPos(x, y)
    u.mouse_event(0x0002, 0, 0, 0, 0)  # левая кнопка вниз
    u.mouse_event(0x0004, 0, 0, 0, 0)  # вверх
    time.sleep(0.05)
    u.SetCursorPos(old.x, old.y)
    for _ in range(6):
        time.sleep(0.5)
        if browser_playing():
            log.info("Видео запущено кликом по плееру")
            return
    send_keys(["k"])  # запасной вариант: фокус уже в плеере
    for _ in range(6):
        time.sleep(0.5)
        if browser_playing():
            log.info("Видео запущено клавишей K")
            return
    log.info("Не удалось запустить видео: звука нет")


def youtube_search_in_tab(text):
    """Поиск на YouTube в текущей вкладке через адресную строку (Ctrl+L): срабатывает, даже если страница
    ещё грузится и поле поиска не в фокусе."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    before = window_automation.window_title(hwnd)
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(text)
    for attempt in range(2):
        # адрес вводится, только если адресная строка действительно получила фокус (иначе буквы ушли бы
        # в страницу YouTube, где это горячие клавиши)
        if not browser_tabs.navigate(hwnd, url):
            time.sleep(0.6)
            continue
        for _ in range(10):  # ждём, что вкладка ушла на страницу результатов
            time.sleep(0.4)
            title = window_automation.window_title(hwnd)
            if title != before and "youtube" in title.lower() and title.lower().startswith(text.lower()[:4]):
                return True
        log.info("Поиск на YouTube не сработал с %d-й попытки, заголовок: %s", attempt + 1, title)
        if not window_automation.is_foreground(hwnd):
            break  # окно потеряло фокус — второй раз вслепую не печатаем
    return False
