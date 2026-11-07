"""Состояние диалога между командами: что ждёт подтверждения, из чего выбирают, что на паузе."""
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.text import Text


@dataclass
class CommandContext:
    settings: dict[str, Any]
    sites: dict[str, str] = field(default_factory=dict)
    apps: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    replies: dict[str, str] = field(default_factory=dict)
    browser_once: str | None = None        # браузер, названный в текущей команде («открой ютуб в хроме»)
    pending: Callable[[], ReplyDTO] | None = None  # что сделать на «да» («выключить компьютер?»)
    choice: list[tuple[str, Any]] | None = None    # варианты, из которых пользователь сейчас выбирает
    youtube_opened_at: float = 0.0         # когда Капри последний раз открывала YouTube
    media_paused: str | None = None        # какой плеер Капри поставила на паузу
    autoscroll_stop: threading.Event | None = None

    def __post_init__(self) -> None:
        self.set_lists(self.settings)

    def set_lists(self, settings: dict[str, Any]) -> None:
        """Сайты, программы, названия и свои ответы из настроек — при запуске и когда config.json поменяли."""
        self.sites = {Text.norm(k): v for k, v in settings.get("sites", {}).items()}
        self.apps = {Text.norm(k): v for k, v in settings.get("apps", {}).items()}
        self.aliases = {Text.norm(k): v for k, v in settings.get("app_aliases", {}).items()}
        self.replies = {Text.norm(k): v for k, v in settings.get("replies", {}).items() if v}

    def book(self, section: str) -> dict[str, str]:
        return {"sites": self.sites, "apps": self.apps, "replies": self.replies}[section]
