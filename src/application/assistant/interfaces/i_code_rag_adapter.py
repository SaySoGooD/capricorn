from abc import ABC, abstractmethod
from typing import Any


class ICodeRagAdapter(ABC):
    """Векторный индекс собственного исходного кода Капри для семантического поиска (RAG).
    Только чтение: индексирует файлы и ищет похожие куски, ничего не меняет."""

    @abstractmethod
    def build(self, force: bool = False) -> bool:
        """Собрать (или подгрузить из кэша) индекс. True — индекс готов. Блокирует, звать в фоне."""
        ...

    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Самые близкие куски кода: [{file, start, text, score}], лучшие первыми."""
        ...

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Что в индексе: {ready, files, chunks, modules} — чтобы отвечать «что у тебя в RAG»."""
        ...
