import re
from abc import ABC, abstractmethod

from src.application.assistant.dto.reply_dto import ReplyDTO


class ISelfKnowledgeUseCase(ABC):
    """Ответы Капри о самой себе по её реальному коду (RAG), без выдумок."""

    @abstractmethod
    def explain(self, c: str, m: re.Match) -> ReplyDTO | None:
        """«что у тебя под капотом», «как у тебя работает X» — ответ по найденным кускам кода."""
        ...

    @abstractmethod
    def rag_info(self, c: str, m: re.Match) -> ReplyDTO | None:
        """«что у тебя в RAG / что ты про себя знаешь» — состав индекса."""
        ...
