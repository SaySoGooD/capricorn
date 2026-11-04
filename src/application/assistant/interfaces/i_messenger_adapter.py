from abc import ABC, abstractmethod


class IMessengerAdapter(ABC):
    @abstractmethod
    def open_chat(self, index: int | None = None, name: str | None = None) -> bool:
        """Открыть чат по имени или номеру в списке. True — открылся."""
        ...
