from src.adapter.windows.keyboard import input_text, send_keys
from src.application.assistant.interfaces.i_keyboard_adapter import IKeyboardAdapter


class WindowsKeyboardAdapter(IKeyboardAdapter):
    def send_keys(self, keys: list[str]) -> None:
        send_keys(keys)

    def input_text(self, text: str) -> None:
        input_text(text)
