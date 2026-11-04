from src.adapter.speech.google_speech_refiner import google_stt
from src.application.assistant.interfaces.i_speech_refiner_adapter import ISpeechRefinerAdapter


class GoogleSpeechRefinerAdapter(ISpeechRefinerAdapter):
    """Отправляет запись фразы в Google — точнее Vosk на вопросах, но нужен интернет."""

    def refine(self, audio: bytes) -> str | None:
        return google_stt(audio)
