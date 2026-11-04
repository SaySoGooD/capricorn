import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IWebCommandsUseCase(ABC):
    """Поиск в интернете, картинки, справка, видео на YouTube."""

    @abstractmethod
    def search(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def images(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def info(self, c: str, m: re.Match) -> ReplyDTO:
        """Открывает поиск Google и вслух пересказывает начало статьи из Википедии, если она нашлась."""
        ...

    @abstractmethod
    def video(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def fallback(self, cmd: str, force_search: bool=False) -> ReplyDTO:
        """Без ответа нейросети: вопрос ищем в Google (если search_when_unsure не выключен),"""
        ...
