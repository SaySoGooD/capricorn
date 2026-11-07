from abc import ABC, abstractmethod


class IAvatarView(ABC):
    """Экранная Капри. Методы можно вызывать из любого потока."""

    @abstractmethod
    def summon(self) -> None: ...

    @abstractmethod
    def vanish(self) -> None: ...

    @abstractmethod
    def set_mode(self, mode: str, seconds: float = 0.0) -> None:
        """idle / listening / thinking / speaking; seconds — сколько слушать."""
        ...

    @abstractmethod
    def set_subtitle(self, text: str) -> None: ...

    @abstractmethod
    def play_anim(self, name: str) -> None: ...

    @abstractmethod
    def roam(self) -> None: ...

    @abstractmethod
    def hop(self) -> None: ...

    @abstractmethod
    def move_to(self, where: str) -> None: ...

    @abstractmethod
    def quit_app(self) -> None: ...

    # экран загрузки: плашка «Инициализация… NN%» без фигуры, пока всё поднимается
    def start_boot(self) -> None: ...

    def set_boot(self, text: str) -> None: ...

    def end_boot(self) -> None: ...

    def launch_effect(self) -> None:
        """Полноэкранная заставка «Капри запустилась»."""
        ...
