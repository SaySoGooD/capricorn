"""Журнал capri.log и окно с ошибкой: Капри запускается без консоли, по-другому о проблеме не узнать.

Модуль не зависит от сторонних библиотек: журнал включается до их импорта, чтобы записать, каких не хватает."""
import logging
import sys
from pathlib import Path

DEFAULT_LOG_FILE = Path(__file__).resolve().parents[2] / "capri.log"


def setup_logging(log_file: str | Path = DEFAULT_LOG_FILE, level: str = "INFO") -> None:
    logging.basicConfig(filename=str(log_file), level=level.upper(), encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(message)s", force=True)
    logging.getLogger("capri").info("Python %s", sys.version.split()[0])


def fatal(text: str) -> None:
    """Показать ошибку окном Windows и выйти."""
    logging.getLogger("capri").error(text)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "Капри не запустилась", 0x10)
    except Exception:
        pass
    sys.exit(1)
