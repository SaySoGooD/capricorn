from abc import ABC, abstractmethod
from typing import Any


class IEmbeddingAdapter(ABC):
    """Векторные представления текста (эмбеддинги) для семантического поиска. Считается на CPU,
    чтобы не отнимать видеопамять у локальной модели."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Готова ли модель эмбеддингов (библиотека установлена и модель загрузилась)."""
        ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[Any] | None:
        """Список векторов (np.ndarray) для каждого текста, либо None, если эмбеддинги недоступны."""
        ...
