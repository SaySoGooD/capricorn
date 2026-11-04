from abc import ABC, abstractmethod


class ISpeakerAdapter(ABC):
    """Синтез голоса Капри."""

    @abstractmethod
    def say(self, text: str) -> bool:
        """Блокирует поток до конца фразы. True — речь перебили."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Перебить: можно вызывать из любого потока."""
        ...

    @abstractmethod
    def prewarm(self, phrases: list[str]) -> None: ...

    @property
    @abstractmethod
    def volume(self) -> int: ...

    @volume.setter
    @abstractmethod
    def volume(self, value: int) -> None: ...

    @property
    @abstractmethod
    def fx(self) -> float: ...

    @fx.setter
    @abstractmethod
    def fx(self, value: float) -> None: ...

    @property
    @abstractmethod
    def last_error(self) -> str | None:
        """Почему не сработал онлайн-голос в последний раз (None — сработал)."""
        ...
