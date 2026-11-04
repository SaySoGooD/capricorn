"""Ответ Капри на команду: что сказать и какое действие выполнить после."""
from dataclasses import dataclass


@dataclass
class ReplyDTO:
    text: str
    action: str | None = None    # "hide" / "quit"
