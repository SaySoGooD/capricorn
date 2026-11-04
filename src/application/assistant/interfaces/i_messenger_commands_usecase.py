import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IMessengerCommandsUseCase(ABC):
    """Чаты Telegram: «первый чат», «чат мама», «открой телеграм папа»."""

    @abstractmethod
    def chat(self, c: str, m: re.Match) -> ReplyDTO:
        """Открывает чат в Telegram (запускает его, если надо)."""
        ...
