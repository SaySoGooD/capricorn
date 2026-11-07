from abc import abstractmethod
from collections.abc import Callable

from src.application.assistant.interfaces.i_chat_model_adapter import IChatModelAdapter


class ILocalChatModelAdapter(IChatModelAdapter):
    """Локальная нейросеть: её сервер нужно запустить, и она умеет болтать сама."""

    @abstractmethod
    def start_server(self) -> None: ...

    @abstractmethod
    def stop_server(self) -> None:
        """Выгрузить модель из памяти (освободить VRAM). Например, на время генерации картинки."""
        ...

    @abstractmethod
    def chatter(self) -> str | None:
        """Короткая спонтанная реплика или None."""
        ...

    def instruct(self, system: str, user: str) -> str | None:
        """Разовый ответ модели на инструкцию (без характера и истории). Напр. подбор тегов для картинки.
        None — если модель недоступна или ответ пустой. По умолчанию не поддерживается."""
        return None

    @abstractmethod
    def set_on_model_change(self, callback: Callable[[str], None]) -> None:
        """Вызвать callback(имя), если пришлось взять другую скачанную модель."""
        ...
