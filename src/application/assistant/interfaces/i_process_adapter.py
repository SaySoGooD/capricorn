from abc import ABC, abstractmethod

from src.application.assistant.dto.process_dto import ProcessGroupDTO, TopProcessesDTO


class IProcessAdapter(ABC):
    """Процессы пользователя (системные и службы адаптер не отдаёт никогда)."""

    @abstractmethod
    def find_groups(self, variants: set[str], words: list[str]) -> list[ProcessGroupDTO]:
        """Программы, похожие на названия variants (и на описание exe по словам words), лучшие первыми."""
        ...

    @abstractmethod
    def kill(self, group: ProcessGroupDTO, force: bool = False) -> str:
        """Завершить: "closed" / "denied" / "failed"."""
        ...

    @abstractmethod
    def top_usage(self, limit: int = 3) -> TopProcessesDTO: ...
