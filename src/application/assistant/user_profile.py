"""Как Капри называет пользователя — по настройке user_name_mode."""
import os
from typing import Any

from src.application.assistant.persona import set_user


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


def apply_user(settings: dict[str, Any]) -> None:
    set_user(user_display_name(settings), settings.get("user_gender", "male"))
