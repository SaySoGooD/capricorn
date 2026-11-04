import ctypes

from src.adapter.windows import window_automation as wa
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter


class WindowsWindowAdapter(IWindowAdapter):
    def foreground_title(self) -> str:
        return wa.foreground_title()

    def foreground_exe(self) -> str | None:
        return wa.window_exe(ctypes.windll.user32.GetForegroundWindow())

    def find_window(self, keywords: tuple[str, ...]) -> int | None:
        return wa.find_window(keywords)

    def wait_and_focus(self, keywords: tuple[str, ...], timeout: float = 10.0) -> int | None:
        return wa.wait_and_focus(keywords, timeout=timeout)

    def minimize_foreground(self) -> None:
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        if hwnd:
            u.ShowWindow(hwnd, 6)  # SW_MINIMIZE

    def close_foreground(self) -> None:
        u = ctypes.windll.user32
        u.keybd_event(0x12, 0, 0, 0)  # Alt
        u.keybd_event(0x73, 0, 0, 0)  # F4
        u.keybd_event(0x73, 0, 2, 0)
        u.keybd_event(0x12, 0, 2, 0)

    def target_window(self) -> int | None:
        return wa.target_window()

    def scroll(self, notches: int, hwnd: int | None = None, delay: float = 0.012) -> None:
        wa.scroll(notches, hwnd=hwnd, delay=delay)

    def screen_notches(self) -> int:
        return wa.screen_notches()

    def focus_search(self, title: str) -> str:
        return wa.focus_search(title)

    def fullscreen_app_active(self) -> bool:
        return wa.fullscreen_app_active()
