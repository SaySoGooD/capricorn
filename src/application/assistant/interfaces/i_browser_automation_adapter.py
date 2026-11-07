from abc import ABC, abstractmethod


class IBrowserAutomationAdapter(ABC):
    """Управление отдельным браузером Капри по Chrome DevTools Protocol: открыть страницу, прочитать
    её содержимое, перечислить и нажать ссылки. Браузер — настоящий Chrome со своим чистым профилем,
    запущенный без флагов автоматизации, чтобы антибот видел обычного пользователя."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Отвечает ли уже отладочный порт браузера (браузер запущен и подключаем)."""
        ...

    @abstractmethod
    def launch(self, timeout: float = 30.0) -> bool:
        """Запустить браузер Капри (если не запущен) и дождаться готовности. True — готов."""
        ...

    @abstractmethod
    def open(self, url: str) -> bool:
        """Открыть URL в браузере Капри и дождаться загрузки."""
        ...

    @abstractmethod
    def page_text(self, limit: int = 8000) -> str | None:
        """Видимый текст текущей страницы (собрать данные). None — если не вышло."""
        ...

    @abstractmethod
    def links(self, limit: int = 60) -> list[tuple[str, str]]:
        """Ссылки текущей страницы [(текст, href)], в порядке появления."""
        ...

    @abstractmethod
    def click_link(self, text: str) -> str | None:
        """Нажать первую ссылку, в тексте которой встречается запрос. Вернёт её href или None."""
        ...

    @abstractmethod
    def current_url(self) -> str | None: ...

    @abstractmethod
    def close(self) -> None:
        """Закрыть браузер Капри."""
        ...
