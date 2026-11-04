from abc import ABC, abstractmethod
from typing import Any

from src.application.assistant.dto.settings_dto import SettingsLoadResultDTO


class ISettingsStore(ABC):
    """Пользовательские настройки (config.json): читаются при запуске и меняются голосом и из трея."""

    @property
    @abstractmethod
    def path(self) -> str: ...

    @abstractmethod
    def load(self) -> SettingsLoadResultDTO:
        """Стандартные настройки, дополненные файлом. Пустой или удалённый файл создаётся заново."""
        ...

    @abstractmethod
    def modified_time(self) -> float | None: ...

    @abstractmethod
    def save_setting(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def save_entry(self, section: str, name: str, value: Any) -> str | None:
        """Свой сайт / программа / ответ; value=None — убрать. Возвращает текст ошибки или None."""
        ...
