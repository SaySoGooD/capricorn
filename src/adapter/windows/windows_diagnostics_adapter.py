from src.adapter.windows.diagnostics import analyze_pc
from src.application.assistant.dto.diagnostics_dto import DiagnosticsDTO
from src.application.assistant.interfaces.i_diagnostics_adapter import IDiagnosticsAdapter


class WindowsDiagnosticsAdapter(IDiagnosticsAdapter):
    def analyze(self) -> DiagnosticsDTO:
        issues, report = analyze_pc()
        return DiagnosticsDTO(issues=issues, report=report)
