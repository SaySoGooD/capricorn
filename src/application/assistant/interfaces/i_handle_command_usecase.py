from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IHandleCommandUseCase(ABC):
    """Разбор фразы: подтверждения и выбор вариантов, свои ответы, цепочки и отдельные команды."""

    @abstractmethod
    def __call__(self, cmd: str) -> ReplyDTO | None:
        ...

    @abstractmethod
    def handle_one(self, c: str) -> ReplyDTO | None:
        ...

    @abstractmethod
    def fallback(self, cmd: str, force_search: bool=False) -> ReplyDTO:
        ...

    @abstractmethod
    def stop_background(self) -> bool:
        ...

    @abstractmethod
    def autoscroll_active(self) -> bool:
        ...
