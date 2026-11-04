import logging
import os
import tempfile

from src.adapter.tts.glitch_sound import make_glitch_sound, play_sound_async
from src.application.assistant.interfaces.i_sound_effects_adapter import ISoundEffectsAdapter

log = logging.getLogger("capri")


class GlitchSoundAdapter(ISoundEffectsAdapter):
    def __init__(self) -> None:
        self._path: str | None = os.path.join(tempfile.gettempdir(), "capri_glitch.wav")

    def prepare_glitch(self, volume: int) -> None:
        if not self._path:
            return
        try:
            make_glitch_sound(self._path, volume)
        except Exception:
            log.info("Звук появления не создан")
            self._path = None

    def play_glitch(self) -> None:
        if self._path:
            play_sound_async(self._path)
