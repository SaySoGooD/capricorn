from abc import ABC, abstractmethod


class ISystemAudioAdapter(ABC):
    """Общая громкость Windows."""

    @abstractmethod
    def get_volume(self) -> int: ...

    @abstractmethod
    def set_volume(self, value: int) -> None: ...

    @abstractmethod
    def set_mute(self, on: bool) -> None: ...
