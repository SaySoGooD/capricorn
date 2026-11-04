from abc import ABC, abstractmethod


class IRememberEntryUseCase(ABC):
    """Записать сайт / программу / свой ответ в config.json и сразу начать их узнавать."""

    @abstractmethod
    def __call__(self, section: str, name: str, target: str | None) -> str | None:
        ...
