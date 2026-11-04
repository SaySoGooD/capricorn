import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IAvatarCommandsUseCase(ABC):
    """Команды самой Капри: уйти, помахать, погулять, переместиться, сказать время."""

    @abstractmethod
    def quit(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def hide(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def wave(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def roam(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def help(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def move(self, c: str, m: re.Match) -> ReplyDTO:
        """Куда переместиться: «в левый нижний угол», «вправо», «в центр», «в другую сторону»."""
        ...

    @abstractmethod
    def time(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def date(self, c: str, m: re.Match) -> ReplyDTO:
        ...
