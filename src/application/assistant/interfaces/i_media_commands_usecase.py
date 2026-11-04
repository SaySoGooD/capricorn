import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IMediaCommandsUseCase(ABC):
    """То, что сейчас играет: музыка, YouTube в браузере, плееры."""

    @abstractmethod
    def media_pause(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def media_play(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def media_next(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def media_prev(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def media_info(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def media_seek(self, c: str, m: re.Match) -> ReplyDTO | None:
        ...
