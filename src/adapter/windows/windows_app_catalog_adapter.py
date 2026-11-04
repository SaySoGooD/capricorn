import os
import subprocess
import threading

from src.adapter.windows.app_catalog import AppIndex
from src.adapter.windows.powershell import NO_WINDOW
from src.application.assistant.dto.app_candidate_dto import AppCandidateDTO, AppTargetDTO
from src.application.assistant.interfaces.i_app_catalog_adapter import IAppCatalogAdapter


def _dto(score: float, name: str, target: tuple[str, str]) -> AppCandidateDTO:
    return AppCandidateDTO(score=score, name=name, target=AppTargetDTO(kind=target[0], value=target[1]))


class WindowsAppCatalogAdapter(IAppCatalogAdapter):
    """Ярлыки «Пуска» и рабочего стола, Get-StartApps и «Программы и компоненты»."""

    def __init__(self) -> None:
        self._index = AppIndex()
        self._started = False

    def start_indexing(self) -> None:
        if not self._started:
            self._started = True
            threading.Thread(target=self._index.build, daemon=True).start()

    def is_ready(self) -> bool:
        return self._index.ready.is_set()

    def wait_ready(self, timeout: float) -> bool:
        return self._index.ready.wait(timeout)

    def candidates(self, query: str, aliases: dict[str, str], limit: int = 4) -> list[AppCandidateDTO]:
        return [_dto(*c) for c in self._index.candidates(query, aliases, limit)]

    def launch(self, target: AppTargetDTO) -> None:
        self._index.launch((target.kind, target.value))

    def launch_best(self, query: str, options: list[AppCandidateDTO]) -> str | None:
        return self._index.launch_best(query, [(o.score, o.name, (o.target.kind, o.target.value)) for o in options])

    def run_target(self, target: str) -> None:
        try:
            os.startfile(target)
        except OSError:
            subprocess.Popen(target, shell=True, creationflags=NO_WINDOW)
