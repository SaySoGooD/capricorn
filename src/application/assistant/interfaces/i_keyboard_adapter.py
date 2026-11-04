from abc import ABC, abstractmethod


class IKeyboardAdapter(ABC):
    @abstractmethod
    def send_keys(self, keys: list[str]) -> None:
        """Зажать клавиши по порядку и отпустить в обратном (Win+Tab и т.п.)."""
        ...

    @abstractmethod
    def input_text(self, text: str) -> None:
        """Ввести текст в активное окно."""
        ...
