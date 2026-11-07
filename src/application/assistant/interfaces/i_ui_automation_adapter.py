from abc import ABC, abstractmethod


class IUiAutomationAdapter(ABC):
    """Клик по элементам окна через UI Automation — кнопки, ссылки, пункты меню, вкладки по их названию."""

    @abstractmethod
    def click_element(self, name: str, hwnd: int | None = None) -> bool:
        """Найти в окне (по умолчанию активном) кликабельный элемент с таким названием и нажать.
        True — получилось, False — элемент не найден или нажать не удалось."""
        ...
