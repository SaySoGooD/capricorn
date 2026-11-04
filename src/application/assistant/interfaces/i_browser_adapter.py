from abc import ABC, abstractmethod


class IBrowserAdapter(ABC):
    @abstractmethod
    def find_browser(self, name: str | None) -> str | None:
        """«хром» / «яндекс браузер» / путь к exe → путь к exe или None, если такого нет."""
        ...

    @abstractmethod
    def open_url(self, url: str, browser_exe: str | None = None) -> None:
        """В указанном браузере или в браузере Windows по умолчанию."""
        ...

    @abstractmethod
    def foreground_page_url(self) -> str | None:
        """Адрес вкладки в активном окне браузера (для «запомни этот сайт»)."""
        ...
