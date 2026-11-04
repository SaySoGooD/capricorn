from abc import ABC, abstractmethod


class ISoundEffectsAdapter(ABC):
    @abstractmethod
    def prepare_glitch(self, volume: int) -> None:
        """(Пере)создать звук появления под громкость Капри 0..100."""
        ...

    @abstractmethod
    def play_glitch(self) -> None: ...
