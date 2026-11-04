from dataclasses import dataclass


@dataclass(frozen=True)
class AppTargetDTO:
    """Что запускать: kind "appid" — приложение из «Пуска» по AppID, "file" — ярлык или exe."""

    kind: str
    value: str


@dataclass(frozen=True)
class AppCandidateDTO:
    """Найденное приложение: оценка похожести 0..1, нормализованное название и цель запуска."""

    score: float
    name: str
    target: AppTargetDTO
