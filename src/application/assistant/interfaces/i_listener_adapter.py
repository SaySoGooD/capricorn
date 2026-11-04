from abc import ABC, abstractmethod


class IListenerAdapter(ABC):
    """Постоянное прослушивание микрофона в своём потоке."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def set_device(self, name: str | None) -> None: ...

    @property
    @abstractmethod
    def active_name(self) -> str | None:
        """Какой микрофон реально открыт."""
        ...

    @property
    @abstractmethod
    def level(self) -> float:
        """Текущая громкость с микрофона 0..1 — для индикатора."""
        ...

    @property
    @abstractmethod
    def gain(self) -> float: ...

    @gain.setter
    @abstractmethod
    def gain(self, value: float) -> None: ...

    @property
    @abstractmethod
    def sensitivity(self) -> int: ...

    @sensitivity.setter
    @abstractmethod
    def sensitivity(self, value: int) -> None: ...

    @abstractmethod
    def mute(self) -> None: ...

    @abstractmethod
    def unmute(self) -> None: ...

    @abstractmethod
    def reset_recognition(self) -> None:
        """Сбросить распознавание — отбросить эхо голоса Капри."""
        ...
