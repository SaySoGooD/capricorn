from abc import ABC, abstractmethod
from collections.abc import Callable

from src.application.assistant.dto.reply_dto import ReplyDTO


class IRunChainUseCase(ABC):
    """«открой телеграм, первый чат, напиши привет» — шаги по очереди, с памятью о текущем окне."""

    @abstractmethod
    def __call__(self, steps: list[str], handle_one: Callable[[str], ReplyDTO | None]) -> ReplyDTO:
        ...
