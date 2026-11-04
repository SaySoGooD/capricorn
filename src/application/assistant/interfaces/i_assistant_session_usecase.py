from abc import ABC, abstractmethod
from typing import Any

from src.application.assistant.interfaces.i_listener_adapter import IListenerAdapter


class IAssistantSessionUseCase(ABC):
    """Капри целиком: слушает, понимает команду, отвечает голосом и иногда появляется сама."""

    @property
    @abstractmethod
    def settings(self) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    def listener(self) -> IListenerAdapter | None:
        ...

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def interrupt(self) -> None:
        ...

    @abstractmethod
    def on_partial(self, text: str) -> None:
        ...

    @abstractmethod
    def on_final(self, text: str, audio: bytes) -> None:
        ...

    @abstractmethod
    def on_listener_error(self, err: Any, kind: str='mic') -> None:
        ...

    @abstractmethod
    def set_profile(self, mode: str, name: str, gender: str) -> None:
        """«Как ко мне обращаться…»: как называть пользователя и в каком роде. Сразу и запоминается."""
        ...

    @abstractmethod
    def set_chatter(self, on: bool) -> None:
        """Появляется ли Капри сама (поболтать, погулять по экрану)."""
        ...

    @abstractmethod
    def set_search_when_unsure(self, on: bool) -> None:
        """Открывать ли Google, когда Капри не знает ответа."""
        ...

    @abstractmethod
    def reload_settings_if_changed(self, speak: bool=True) -> None:
        """Правки config.json (сайты, программы, названия) подхватываются без перезапуска."""
        ...

    @abstractmethod
    def current_mic(self) -> str:
        ...

    @abstractmethod
    def input_devices(self) -> list[str]:
        ...

    @abstractmethod
    def default_input_name(self) -> str:
        ...

    @abstractmethod
    def set_mic(self, name: str | None, announce: bool=True) -> None:
        """Сменить устройство ввода на ходу и запомнить выбор (None — как в Windows по умолчанию)."""
        ...

    @abstractmethod
    def set_mic_tuning(self, gain: float | None=None, sensitivity: int | None=None) -> None:
        """Громкость ввода и чувствительность микрофона для Капри — сразу и запоминаются."""
        ...

    @abstractmethod
    def set_voice_fx(self, strength: float) -> None:
        """Сила цифровых эффектов голоса: 0 — чистый голос, 1.8 — как задумано, больше — сильнее."""
        ...

    @abstractmethod
    def set_voice_volume(self, volume: int) -> None:
        """Громкость голоса Капри 0..100 — только её, общая громкость Windows не меняется."""
        ...

    @abstractmethod
    def call_from_click(self) -> None:
        ...

    @abstractmethod
    def text_command(self, text: str) -> None:
        ...

    @abstractmethod
    def say_later(self, text: str) -> None:
        """Сказать в рабочем потоке (не блокируя окно, из которого попросили)."""
        ...

    @abstractmethod
    def say(self, text: str) -> bool:
        """Озвучивает текст. Возвращает True, если Капри перебили."""
        ...
