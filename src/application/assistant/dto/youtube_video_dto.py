from dataclasses import dataclass


@dataclass(frozen=True)
class YouTubeVideoDTO:
    video_id: str
    title: str
