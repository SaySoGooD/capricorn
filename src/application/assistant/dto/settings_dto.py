from dataclasses import dataclass, field
from typing import Any


@dataclass
class SettingsLoadResultDTO:
    """Настройки из config.json поверх стандартных и что сказать вслух, если файл не прочитался."""

    settings: dict[str, Any] = field(default_factory=dict)
    error: str = ""
