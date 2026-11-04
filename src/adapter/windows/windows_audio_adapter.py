from src.adapter.windows.audio_endpoint import get_volume, set_mute, set_volume
from src.application.assistant.interfaces.i_system_audio_adapter import ISystemAudioAdapter


class WindowsAudioAdapter(ISystemAudioAdapter):
    """Общая громкость Windows через pycaw."""

    def get_volume(self) -> int:
        return get_volume()

    def set_volume(self, value: int) -> None:
        set_volume(value)

    def set_mute(self, on: bool) -> None:
        set_mute(on)
