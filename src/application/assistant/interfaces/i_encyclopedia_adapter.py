from abc import ABC, abstractmethod


class IEncyclopediaAdapter(ABC):
    @abstractmethod
    def summary(self, query: str, sentences: int = 2) -> str | None:
        """Начало статьи, подготовленное для озвучки, или None."""
        ...
