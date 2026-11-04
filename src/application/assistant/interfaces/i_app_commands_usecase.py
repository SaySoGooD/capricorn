import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IAppCommandsUseCase(ABC):
    """Программы, сайты, папки и файлы: открыть, закрыть, снять задачу, создать."""

    @abstractmethod
    def answer_choice(self, c: str) -> ReplyDTO | None:
        """Ответ на «какое открыть / закрыть?». None — это не выбор, а новая команда."""
        ...

    @abstractmethod
    def open(self, c: str, m: re.Match) -> ReplyDTO | None:
        ...

    @abstractmethod
    def kill_process(self, c: str, m: re.Match) -> ReplyDTO:
        """«сними задачу steam client helper», «заверши процесс хром принудительно», «кильни дискорд»."""
        ...

    @abstractmethod
    def close(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def create(self, c: str, m: re.Match) -> ReplyDTO | None:
        ...
