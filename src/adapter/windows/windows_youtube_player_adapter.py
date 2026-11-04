import threading
import time

from src.adapter.windows import browser_tabs, window_automation, youtube_player
from src.adapter.windows.audio_endpoint import browser_playing
from src.adapter.windows.keyboard import send_keys
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter


class WindowsYouTubePlayerAdapter(IYouTubePlayerAdapter):
    def window_present(self) -> bool:
        return bool(window_automation.find_window(("youtube",)))

    def browser_playing(self) -> bool:
        return browser_playing()

    def press_player_keys(self, keys_list: list[list[str]]) -> bool:
        hwnd = window_automation.find_window(("youtube",))
        if not hwnd or not window_automation.focus(hwnd):
            return False
        for keys in keys_list:
            send_keys(keys)
            time.sleep(0.12)
        return True

    def ensure_playing_async(self, wait_load: float = 7.0) -> None:
        threading.Thread(target=youtube_player.ensure_playing, args=(wait_load,), daemon=True).start()

    def cancel_ensure(self) -> None:
        youtube_player.cancel_ensure()

    def search_in_tab(self, text: str) -> bool:
        return youtube_player.youtube_search_in_tab(text)

    def seek_by_url(self, seconds: float) -> bool:
        return browser_tabs.youtube_url_seek(seconds)
