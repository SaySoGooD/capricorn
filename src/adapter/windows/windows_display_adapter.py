from src.adapter.windows.display import get_brightness, set_brightness
from src.application.assistant.interfaces.i_display_adapter import IDisplayAdapter


class WindowsDisplayAdapter(IDisplayAdapter):
    def get_brightness(self) -> int:
        return get_brightness()

    def set_brightness(self, value: int) -> None:
        set_brightness(value)
