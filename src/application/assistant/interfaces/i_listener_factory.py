from abc import ABC, abstractmethod

from src.application.assistant.dto.listener_dto import ListenerCallbacksDTO
from src.application.assistant.interfaces.i_listener_adapter import IListenerAdapter


class IListenerFactory(ABC):
    @abstractmethod
    def model_exists(self) -> bool:
        """Есть ли модель распознавания речи."""
        ...

    @abstractmethod
    def create(
        self,
        callbacks: ListenerCallbacksDTO,
        device_name: str | None,
        gain: float,
        sensitivity: int,
    ) -> IListenerAdapter: ...
