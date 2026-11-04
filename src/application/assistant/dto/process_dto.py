from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcessGroupDTO:
    """Процессы одной программы, подходящие под название из речи. handles — объекты адаптера."""

    name: str
    score: float
    handles: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class ProcessUsageDTO:
    name: str
    value: float


@dataclass(frozen=True)
class TopProcessesDTO:
    """Самые тяжёлые процессы: cpu — проценты, memory — мегабайты."""

    cpu: list[ProcessUsageDTO]
    memory: list[ProcessUsageDTO]
