from src.adapter.web.youtube_search import youtube_first
from src.application.assistant.dto.youtube_video_dto import YouTubeVideoDTO
from src.application.assistant.interfaces.i_youtube_search_adapter import IYouTubeSearchAdapter


class YouTubeSearchAdapter(IYouTubeSearchAdapter):
    def first_video(self, query: str) -> YouTubeVideoDTO | None:
        found = youtube_first(query)
        return YouTubeVideoDTO(video_id=found[0], title=found[1]) if found else None
