"""Журнал capri.log и окно с ошибкой: Капри запускается без консоли, по-другому о проблеме не узнать.

Модуль не зависит от сторонних библиотек: журнал включается до их импорта, чтобы записать, каких не хватает."""
import faulthandler
import logging
import sys
import threading
from pathlib import Path

log = logging.getLogger("capri")


class _LogWriter:
    """Поток вывода, который пишет в журнал. Нужен под pythonw, где sys.stdout и sys.stderr равны None:
    любой print или traceback в стороннем коде иначе роняет поток молча, без следа в журнале."""

    def __init__(self, level: int, name: str) -> None:
        self._level, self._name, self._buf = level, name, ""

    def write(self, text: str) -> int:
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                log.log(self._level, "[%s] %s", self._name, line)
        return len(text)

    def flush(self) -> None:
        if self._buf.strip():
            log.log(self._level, "[%s] %s", self._name, self._buf.strip())
        self._buf = ""

    def isatty(self) -> bool:
        return False


class Diagnostics:
    """Журнал и перехват аварий. Без состояния экземпляра — методы статические; живёт один на процесс."""

    DEFAULT_LOG_FILE = Path(__file__).resolve().parents[2] / "capri.log"
    # подробный формат: время, уровень, поток, откуда вызвано, текст — чтобы находить, где именно падает
    VERBOSE_FORMAT = ("%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s "
                      "%(module)s:%(funcName)s:%(lineno)d  %(message)s")
    _fault_file = None  # держим файл открытым, пока жив процесс, иначе faulthandler пишет в закрытый дескриптор

    @staticmethod
    def setup_logging(log_file: str | Path = DEFAULT_LOG_FILE, level: str = "DEBUG") -> None:
        logging.basicConfig(filename=str(log_file), level=level.upper(), encoding="utf-8",
                            format=Diagnostics.VERBOSE_FORMAT, force=True)
        log.info("Python %s | pythonw=%s | stdout=%s", sys.version.split()[0],
                 sys.executable.lower().endswith("pythonw.exe"), sys.stdout)

    @staticmethod
    def install_crash_handlers(log_file: str | Path = DEFAULT_LOG_FILE) -> None:
        """Ловит всё, что обычно теряется: вывод в несуществующую консоль, необработанные исключения
        в главном и фоновых потоках, жёсткие аварии (segfault) и смерть процесса."""
        # 1) под pythonw stdout/stderr — None; направляем их в журнал, чтобы сторонние print/traceback не роняли поток
        if sys.stdout is None:
            sys.stdout = _LogWriter(logging.INFO, "stdout")
        if sys.stderr is None:
            sys.stderr = _LogWriter(logging.ERROR, "stderr")

        # 2) жёсткие аварии (C-уровень: segfault, abort) — отдельный файл, дописываем
        try:
            Diagnostics._fault_file = open(Path(log_file).with_name("capri.fault.log"), "a", encoding="utf-8")
            faulthandler.enable(Diagnostics._fault_file)
        except Exception:
            log.exception("faulthandler не включился")

        # 3) необработанные исключения в главном потоке
        def on_exception(exc_type, exc, tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc, tb)
                return
            log.critical("НЕОБРАБОТАННОЕ исключение в главном потоке", exc_info=(exc_type, exc, tb))

        sys.excepthook = on_exception

        # 4) необработанные исключения в фоновых потоках (Qt, звук, TTS)
        def on_thread_exception(args):
            log.critical("НЕОБРАБОТАННОЕ исключение в потоке %s", getattr(args.thread, "name", "?"),
                         exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

        threading.excepthook = on_thread_exception
        log.info("Диагностика включена: перехват stdout/stderr, excepthook, faulthandler")

    @staticmethod
    def log_qt_messages() -> None:
        """Перенаправить предупреждения и ошибки самого Qt в журнал. Вызывать после импорта PySide6."""
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler

        levels = {QtMsgType.QtDebugMsg: logging.DEBUG, QtMsgType.QtInfoMsg: logging.INFO,
                  QtMsgType.QtWarningMsg: logging.WARNING, QtMsgType.QtCriticalMsg: logging.ERROR,
                  QtMsgType.QtFatalMsg: logging.CRITICAL}

        def handler(mode, ctx, message):
            where = f" ({ctx.file}:{ctx.line})" if ctx.file else ""
            log.log(levels.get(mode, logging.INFO), "[Qt] %s%s", message, where)

        qInstallMessageHandler(handler)

    @staticmethod
    def fatal(text: str) -> None:
        """Показать ошибку окном Windows и выйти."""
        log.error(text)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, "Капри не запустилась", 0x10)
        except Exception:
            pass
        sys.exit(1)
