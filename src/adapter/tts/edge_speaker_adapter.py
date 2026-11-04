from typing import Any

from src.adapter.tts.edge_speaker import Speaker
from src.application.assistant.interfaces.i_speaker_adapter import ISpeakerAdapter


class EdgeSpeakerAdapter(ISpeakerAdapter):
    """Голос Microsoft Edge TTS с запасными Silero и SAPI."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self._speaker = Speaker(settings)

    def say(self, text: str) -> bool:
        return self._speaker.say(text)

    def stop(self) -> None:
        self._speaker.stop()

    def prewarm(self, phrases: list[str]) -> None:
        self._speaker.prewarm(phrases)

    @property
    def volume(self) -> int:
        return self._speaker.volume

    @volume.setter
    def volume(self, value: int) -> None:
        self._speaker.volume = value

    @property
    def fx(self) -> float:
        return self._speaker.fx

    @fx.setter
    def fx(self, value: float) -> None:
        self._speaker.fx = value

    @property
    def last_error(self) -> str | None:
        return self._speaker.edge_error
