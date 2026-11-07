import ctypes
import subprocess
import webbrowser

from src.adapter.windows import browser_tabs
from src.adapter.windows.browser_launcher import find_browser
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter


class WindowsBrowserAdapter(IBrowserAdapter):
    def find_browser(self, name: str | None) -> str | None:
        return find_browser(name)

    def open_url(self, url: str, browser_exe: str | None = None) -> None:
        if browser_exe:
            subprocess.Popen([browser_exe, url])
        else:
            webbrowser.open(url)

    def foreground_page_url(self) -> str | None:
        return browser_tabs.page_url(ctypes.windll.user32.GetForegroundWindow())

    def switch_tab(self, n: int) -> None:
        browser_tabs.switch_tab(n)
