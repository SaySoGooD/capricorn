from abc import ABC, abstractmethod


class IChatModelAdapter(ABC):
    """Нейросеть для ответов на вопросы."""

    @property
    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def ask(self, question: str) -> str | None:
        """Текст ответа или None, если лучше открыть поиск."""
        ...

    @abstractmethod
    def summarize_report(self, report: str) -> str | None: ...
