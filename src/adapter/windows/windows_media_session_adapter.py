from src.adapter.windows import media_session
from src.application.assistant.dto.media_dto import MediaControlResultDTO, MediaSeekResultDTO, NowPlayingDTO
from src.application.assistant.interfaces.i_media_session_adapter import IMediaSessionAdapter


class WindowsMediaSessionAdapter(IMediaSessionAdapter):
    """Системные мультимедиа-элементы Windows (winrt GlobalSystemMediaTransportControls)."""

    def now_playing(self) -> NowPlayingDTO | None:
        info = media_session.now_playing()
        return NowPlayingDTO(title=info[0] or "", source=info[1], playing=bool(info[2])) if info else None

    def control(self, action: str, source: str | None = None) -> MediaControlResultDTO:
        ok, title, src = media_session.control(action, source=source)
        return MediaControlResultDTO(ok=bool(ok), title=title, source=src)

    def seek(self, seconds: float | None = None, delta: float | None = None) -> MediaSeekResultDTO:
        ok, position, src = media_session.seek(seconds=seconds, delta=delta)
        return MediaSeekResultDTO(ok=bool(ok), position=position, source=src)
