import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IMemoryCommandsUseCase(ABC):
    """Свои сайты, программы и ответы: «запомни этот сайт как музыка», «когда я скажу X, отвечай Y»."""

    @abstractmethod
    def custom_reply(self, c: str) -> ReplyDTO | None:
        """Свой ответ на фразу из config.json → "replies" (точно или почти дословно) или None."""
        ...

    @abstractmethod
    def remember_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        """«запомни этот сайт как музыка» — адрес открытой вкладки; «запомни эту программу как запрет» —"""
        ...

    @abstractmethod
    def forget_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def updates(self, c: str, m: re.Match) -> ReplyDTO:
        """Страница Капри на GitHub — там новые версии."""
        ...

    @abstractmethod
    def reply_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        """«Когда я скажу „как дела“, отвечай „лучше всех“» — свой ответ на фразу."""
        ...

    @abstractmethod
    def forget_reply_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        ...
