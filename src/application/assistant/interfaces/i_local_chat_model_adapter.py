from abc import abstractmethod
from collections.abc import Callable

from src.application.assistant.interfaces.i_chat_model_adapter import IChatModelAdapter


class ILocalChatModelAdapter(IChatModelAdapter):
    """Локальная нейросеть: её сервер нужно запустить, и она умеет болтать сама."""

    @abstractmethod
    def start_server(self) -> None: ...

    @abstractmethod
    def chatter(self) -> str | None:
        """Короткая спонтанная реплика или None."""
        ...

    @abstractmethod
    def set_on_model_change(self, callback: Callable[[str], None]) -> None:
        """Вызвать callback(имя), если пришлось взять другую скачанную модель."""
        ...
