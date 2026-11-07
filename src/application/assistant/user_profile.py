"""Как Капри называет пользователя — по настройке user_name_mode."""
import os
from typing import Any

from src.application.assistant.persona import persona


class UserProfile:
    """Имя пользователя для обращения — из настроек. Без состояния; настраивает общий ``persona``."""

    @staticmethod
    def user_display_name(settings: dict[str, Any]) -> str:
        """"custom" — user_name, "windows" — имя пользователя Windows, "pc" — имя компьютера, "none" — не называть."""
        mode = settings.get("user_name_mode", "none")
        if mode == "custom":
            return settings.get("user_name", "").strip()
        if mode == "windows":
            return os.environ.get("USERNAME", "")
        if mode == "pc":
            return os.environ.get("COMPUTERNAME", "")
        return ""

    @staticmethod
    def apply_user(settings: dict[str, Any]) -> None:
        persona.set_user(UserProfile.user_display_name(settings), settings.get("user_gender", "male"))
