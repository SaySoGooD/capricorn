from abc import ABC, abstractmethod

from src.application.assistant.dto.app_candidate_dto import AppCandidateDTO, AppTargetDTO


class IAppCatalogAdapter(ABC):
    """Установленные программы и их запуск."""

    @abstractmethod
    def start_indexing(self) -> None:
        """Собрать список программ в фоне."""
        ...

    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    def wait_ready(self, timeout: float) -> bool: ...

    @abstractmethod
    def candidates(self, query: str, aliases: dict[str, str], limit: int = 4) -> list[AppCandidateDTO]:
        """Подходящие приложения, лучшие первыми."""
        ...

    @abstractmethod
    def launch(self, target: AppTargetDTO) -> None: ...

    @abstractmethod
    def launch_best(self, query: str, options: list[AppCandidateDTO]) -> str | None:
        """Запустить лучший вариант (с запасными путями). Имя запущенного или None."""
        ...

    @abstractmethod
    def run_target(self, target: str) -> None:
        """Свой пункт из настроек "apps": путь, команда или shell:-адрес."""
        ...
