from abc import ABC, abstractmethod


class IDisplayAdapter(ABC):
    @abstractmethod
    def get_brightness(self) -> int: ...

    @abstractmethod
    def set_brightness(self, value: int) -> None: ...
