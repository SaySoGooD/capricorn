from abc import ABC, abstractmethod


class IScreenshotAdapter(ABC):
    @abstractmethod
    def capture(self) -> str:
        """Снимок всех экранов. Возвращает путь к файлу."""
        ...
