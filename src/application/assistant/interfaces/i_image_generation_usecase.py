import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class IImageGenerationUseCase(ABC):
    @abstractmethod
    def draw(self, c: str, m: re.Match) -> ReplyDTO:
        """«нарисуй …» / «сгенерируй картинку …» — сгенерировать изображение по описанию."""
        ...

    @abstractmethod
    def start_server(self, c: str, m: re.Match) -> ReplyDTO:
        """«запусти ComfyUI» — поднять сервер генерации картинок."""
        ...

    @abstractmethod
    def stop_server(self, c: str, m: re.Match) -> ReplyDTO:
        """«выгрузи ComfyUI» — остановить сервер и освободить видеопамять."""
        ...
