from abc import ABC, abstractmethod

from src.application.assistant.dto.diagnostics_dto import DiagnosticsDTO


class IDiagnosticsAdapter(ABC):
    @abstractmethod
    def analyze(self) -> DiagnosticsDTO: ...
