from abc import ABC, abstractmethod


class IYouTubePlayerAdapter(ABC):
    """YouTube, открытый в браузере."""

    @abstractmethod
    def window_present(self) -> bool: ...

    @abstractmethod
    def browser_playing(self) -> bool:
        """Идёт ли сейчас звук из браузера."""
        ...

    @abstractmethod
    def press_player_keys(self, keys_list: list[list[str]]) -> bool:
        """Горячие клавиши плеера в его окне (k — пауза, j/l — ±10 с, стрелки — ±5 с)."""
        ...

    @abstractmethod
    def ensure_playing_async(self, wait_load: float = 7.0) -> None:
        """В фоне дождаться звука, а если тишина — запустить видео кликом по плееру."""
        ...

    @abstractmethod
    def cancel_ensure(self) -> None: ...

    @abstractmethod
    def search_in_tab(self, text: str) -> bool:
        """Поиск на YouTube в текущей вкладке через адресную строку."""
        ...

    @abstractmethod
    def seek_by_url(self, seconds: float) -> bool:
        """Открыть то же видео с меткой времени t."""
        ...
