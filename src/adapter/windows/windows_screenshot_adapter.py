import datetime
import os

from src.application.assistant.interfaces.i_screenshot_adapter import IScreenshotAdapter


class WindowsScreenshotAdapter(IScreenshotAdapter):
    def __init__(self, folder: str) -> None:
        self._folder = folder

    def capture(self) -> str:
        from PIL import ImageGrab

        os.makedirs(self._folder, exist_ok=True)
        path = os.path.join(self._folder, f"screen_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
        ImageGrab.grab(all_screens=True).save(path)
        return path
