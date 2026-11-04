"""Повторное распознавание фразы через Google — точнее Vosk на вопросах (нужен интернет)."""
import logging

from src.adapter.speech.vosk_listener import RATE

log = logging.getLogger("capri")


def google_stt(audio, language="ru-RU"):
    """Повторно распознаёт фразу через Google — точнее Vosk на вопросах. None при ошибке."""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        r.operation_timeout = 6
        return r.recognize_google(sr.AudioData(audio, RATE, 2), language=language)
    except Exception as e:
        log.info("Google STT недоступен: %s", e)
        return None
