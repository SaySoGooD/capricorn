from abc import ABC, abstractmethod

from src.application.assistant.dto.media_dto import MediaControlResultDTO, MediaSeekResultDTO, NowPlayingDTO


class IMediaSessionAdapter(ABC):
    """Системные мультимедиа-элементы: музыка, YouTube в браузере, плееры."""

    @abstractmethod
    def now_playing(self) -> NowPlayingDTO | None: ...

    @abstractmethod
    def control(self, action: str, source: str | None = None) -> MediaControlResultDTO:
        """pause / play / toggle / next / prev."""
        ...

    @abstractmethod
    def seek(self, seconds: float | None = None, delta: float | None = None) -> MediaSeekResultDTO: ...
