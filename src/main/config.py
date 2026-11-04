from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    """Пути и параметры запуска. Переопределяются переменными окружения или файлом .env в папке Капри.
    Пользовательские настройки (сайты, голос, микрофон…) — в config.json, см. JsonSettingsStore."""

    BASE_DIR: str = str(BASE_DIR)
    SETTINGS_FILE: str = "config.json"
    ASSETS_DIR: str = "assets"
    REPORTS_DIR: str = "reports"
    SCREENSHOTS_DIR: str = str(Path.home() / "Pictures" / "Capri")

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "capri.log"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def resolve_paths(self) -> "Config":
        """Относительные пути — от папки Капри, а не от текущей папки (run.bat запускают откуда угодно)."""
        base = Path(self.BASE_DIR)
        for field in ("SETTINGS_FILE", "ASSETS_DIR", "REPORTS_DIR", "SCREENSHOTS_DIR", "LOG_FILE"):
            path = Path(getattr(self, field))
            if not path.is_absolute():
                setattr(self, field, str(base / path))
        return self

    @staticmethod
    def get_object() -> "Config":
        return Config()
