from src.adapter.windows.telegram_messenger import telegram_open_chat
from src.application.assistant.interfaces.i_messenger_adapter import IMessengerAdapter


class TelegramMessengerAdapter(IMessengerAdapter):
    """Telegram Desktop через UI Automation и клавиатуру."""

    def open_chat(self, index: int | None = None, name: str | None = None) -> bool:
        return telegram_open_chat(index=index, name=name)
