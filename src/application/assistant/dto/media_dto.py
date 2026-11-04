from dataclasses import dataclass


@dataclass(frozen=True)
class NowPlayingDTO:
    """Что сейчас в системных мультимедиа-элементах Windows."""

    title: str
    source: str | None
    playing: bool


@dataclass(frozen=True)
class MediaControlResultDTO:
    ok: bool
    title: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class MediaSeekResultDTO:
    ok: bool
    position: float | None = None
    source: str | None = None
