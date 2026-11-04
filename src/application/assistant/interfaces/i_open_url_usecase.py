from abc import ABC, abstractmethod


class IOpenUrlUseCase(ABC):
    """Открыть адрес: в браузере из команды («… в хроме»), из настройки "browser" или в браузере"""

    @abstractmethod
    def __call__(self, url: str) -> None:
        ...
