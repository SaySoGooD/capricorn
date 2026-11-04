from src.adapter.speech.vosk_listener import default_input_name, input_devices
from src.application.assistant.interfaces.i_audio_devices_adapter import IAudioDevicesAdapter


class SoundDeviceAudioDevicesAdapter(IAudioDevicesAdapter):
    def input_devices(self) -> list[str]:
        return [name for name, _ in input_devices()]

    def default_input_name(self) -> str:
        return default_input_name()
