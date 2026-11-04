import os
from typing import Any

from src.adapter.speech.vosk_listener import Listener
from src.application.assistant.dto.listener_dto import ListenerCallbacksDTO
from src.application.assistant.interfaces.i_listener_adapter import IListenerAdapter
from src.application.assistant.interfaces.i_listener_factory import IListenerFactory


class VoskListenerAdapter(IListenerAdapter):
    def __init__(self, listener: Listener) -> None:
        self._listener = listener

    def start(self) -> None:
        self._listener.start()

    def set_device(self, name: str | None) -> None:
        self._listener.set_device(name)

    @property
    def active_name(self) -> str | None:
        return self._listener.active_name

    @property
    def level(self) -> float:
        return self._listener.level

    @property
    def gain(self) -> float:
        return self._listener.gain

    @gain.setter
    def gain(self, value: float) -> None:
        self._listener.gain = value

    @property
    def sensitivity(self) -> int:
        return self._listener.sensitivity

    @sensitivity.setter
    def sensitivity(self, value: int) -> None:
        self._listener.sensitivity = value

    def mute(self) -> None:
        self._listener.muted.set()

    def unmute(self) -> None:
        self._listener.muted.clear()

    def reset_recognition(self) -> None:
        self._listener.reset_req.set()


class VoskListenerFactory(IListenerFactory):
    """Модель Vosk лежит в папке Капри (путь из настройки vosk_model)."""

    def __init__(self, base_dir: str, settings: dict[str, Any]) -> None:
        self._base_dir = base_dir
        self._settings = settings

    def _model_path(self) -> str:
        return os.path.join(self._base_dir, self._settings["vosk_model"])

    def model_exists(self) -> bool:
        return os.path.isdir(self._model_path())

    def create(
        self,
        callbacks: ListenerCallbacksDTO,
        device_name: str | None,
        gain: float,
        sensitivity: int,
    ) -> IListenerAdapter:
        return VoskListenerAdapter(Listener(
            self._model_path(), callbacks.on_final, callbacks.on_partial, callbacks.on_error,
            device_name=device_name, gain=gain, sensitivity=sensitivity,
        ))
