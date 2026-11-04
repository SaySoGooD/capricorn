from abc import ABC, abstractmethod


class IZapretAdapter(ABC):
    """zapret (winws.exe) иногда ломает соединение с сервером голоса Microsoft."""

    @abstractmethod
    def is_network_error(self, error: str) -> bool: ...

    @abstractmethod
    def running(self) -> bool: ...

    @abstractmethod
    def find_all_lists(self) -> list[str]: ...

    @abstractmethod
    def excluded(self, lists: str) -> bool: ...

    @abstractmethod
    def add_exclude(self, lists: str) -> str: ...
