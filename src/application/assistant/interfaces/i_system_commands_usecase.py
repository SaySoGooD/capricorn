import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class ISystemCommandsUseCase(ABC):
    """Компьютер: питание, блокировка, громкость, яркость, диагностика, скриншот, тяжёлые процессы."""

    @abstractmethod
    def power(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def lock(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def volume(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def brightness(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def analyze(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def screenshot(self, c: str, m: re.Match) -> ReplyDTO:
        ...

    @abstractmethod
    def top_processes(self, c: str, m: re.Match) -> ReplyDTO:
        """«Что грузит компьютер» — три процесса, которые больше всего едят процессор и память."""
        ...
