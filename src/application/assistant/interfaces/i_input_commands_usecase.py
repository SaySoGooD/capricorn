import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IInputCommandsUseCase(ABC):
    """Клавиатура, прокрутка, окна и вкладки, печать текста."""

    @abstractmethod
    def scroll(self, c: str, m: re.Match) -> ReplyDTO | None:
        ...

    @abstractmethod
    def autoscroll_active(self) -> bool:
        ...

    @abstractmethod
    def stop_background(self) -> bool:
        """Остановить фоновые действия (автопрокрутку). True — было что останавливать."""
        ...

    @abstractmethod
    def press(self, c: str, m: re.Match) -> ReplyDTO | None:
        ...

    @abstractmethod
    def tab(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def minimize_all(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def minimize(self, c: str, m: re.Match) -> ReplyDTO:
        """«Сверни окно / вкладку / браузер» — сворачивает активное окно."""
        ...

    @abstractmethod
    def search_field(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def type_cmd(self, c: str, m: re.Match) -> ReplyDTO | None:
        """«напиши привет» — печатает в активное окно и жмёт Enter (в чате это отправка)."""
        ...
