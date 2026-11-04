from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticsDTO:
    """Итог диагностики ПК: проблемы для озвучки и полный текстовый отчёт."""

    issues: list[str]
    report: str
