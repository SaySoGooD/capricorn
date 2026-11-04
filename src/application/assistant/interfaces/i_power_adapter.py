from abc import ABC, abstractmethod


class IPowerAdapter(ABC):
    @abstractmethod
    def shutdown(self, restart: bool) -> None:
        """Выключить или перезагрузить компьютер через 10 секунд."""
        ...

    @abstractmethod
    def lock(self) -> None: ...
