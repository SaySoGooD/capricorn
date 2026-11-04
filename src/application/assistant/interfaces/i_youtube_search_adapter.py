from abc import ABC, abstractmethod

from src.application.assistant.dto.youtube_video_dto import YouTubeVideoDTO


class IYouTubeSearchAdapter(ABC):
    @abstractmethod
    def first_video(self, query: str) -> YouTubeVideoDTO | None:
        """Первое обычное видео (не шортс) из поиска YouTube."""
        ...
