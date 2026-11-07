import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IBrowserAutomationUseCase(ABC):
    """Голосовое управление собственным браузером Капри (CDP): открыть, прочитать, ссылки, клик, закрыть."""

    @abstractmethod
    def open_browser(self, c: str, m: re.Match) -> ReplyDTO | None: ...

    @abstractmethod
    def open_site(self, c: str, m: re.Match) -> ReplyDTO | None: ...

    @abstractmethod
    def read_page(self, c: str, m: re.Match) -> ReplyDTO | None: ...

    @abstractmethod
    def list_links(self, c: str, m: re.Match) -> ReplyDTO | None: ...

    @abstractmethod
    def click_link(self, c: str, m: re.Match) -> ReplyDTO | None: ...

    @abstractmethod
    def close_browser(self, c: str, m: re.Match) -> ReplyDTO | None: ...
