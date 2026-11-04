from abc import ABC, abstractmethod


class IWindowAdapter(ABC):
    """Окна Windows. hwnd — непрозрачный идентификатор окна."""

    @abstractmethod
    def foreground_title(self) -> str: ...

    @abstractmethod
    def foreground_exe(self) -> str | None:
        """Полный путь к программе активного окна."""
        ...

    @abstractmethod
    def find_window(self, keywords: tuple[str, ...]) -> int | None: ...

    @abstractmethod
    def wait_and_focus(self, keywords: tuple[str, ...], timeout: float = 10.0) -> int | None: ...

    @abstractmethod
    def minimize_foreground(self) -> None: ...

    @abstractmethod
    def close_foreground(self) -> None:
        """Alt+F4 активному окну."""
        ...

    @abstractmethod
    def target_window(self) -> int | None:
        """Окно, с которым работает пользователь (не сама Капри)."""
        ...

    @abstractmethod
    def scroll(self, notches: int, hwnd: int | None = None, delay: float = 0.012) -> None: ...

    @abstractmethod
    def screen_notches(self) -> int:
        """Сколько щелчков колеса — примерно один экран."""
        ...

    @abstractmethod
    def focus_search(self, title: str) -> str:
        """Курсор в поиск текущего окна. Возвращает youtube / telegram / browser."""
        ...

    @abstractmethod
    def fullscreen_app_active(self) -> bool: ...
