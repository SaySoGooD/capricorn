"""Запуск Капри: журнал, Qt, контейнер зависимостей, трей и сессия ассистента."""
import ctypes
import logging
import sys

from src.main.logging_setup import Diagnostics

log = logging.getLogger("capri")


class App:
    """Точка входа Капри: поднимает журнал, проверяет единственность экземпляра и крутит цикл событий Qt."""

    INSTANCE_MUTEX = "Capri-Single-Instance-Mutex"

    def __init__(self) -> None:
        self._mutex_handle = None  # держим дескриптор живым весь процесс, иначе Windows снимет блокировку

    def _is_only_instance(self) -> bool:
        """True, если других запущенных Капри нет. Именованный мьютекс Windows снимается сам при выходе процесса,
        поэтому после падения блокировка не остаётся."""
        try:
            self._mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, App.INSTANCE_MUTEX)
            return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
        except Exception:
            log.exception("Проверка единственного экземпляра не сработала — запускаюсь как есть")
            return True

    def _main(self) -> None:
        # журнал — до всех библиотек: если какой-то не хватает, Капри падает без окна, и узнать причину можно только тут
        Diagnostics.setup_logging()
        Diagnostics.install_crash_handlers()
        if not self._is_only_instance():
            log.warning("Капри уже запущена — второй экземпляр не стартует")
            try:
                ctypes.windll.user32.MessageBoxW(None, "Капри уже запущена.", "Капри", 0x40)
            except Exception:
                pass
            sys.exit(0)
        try:
            from PySide6.QtWidgets import QApplication

            from src.main.dependency_injection import container
        except ImportError as e:
            log.exception("Не хватает библиотек")
            Diagnostics.fatal(f"Не установлены нужные библиотеки ({e.name or e}).\n\n"
                              f"Запусти setup.bat в папке Капри и дождись надписи «Готово», потом снова run.bat.\n"
                              f"Если setup.bat выдаёт ошибку — сфотографируй его окно.\n\nPython {sys.version.split()[0]}")
            return

        log.debug("Библиотеки импортированы, читаю конфиг")
        config = container.config()
        Diagnostics.setup_logging(config.LOG_FILE, config.LOG_LEVEL)
        Diagnostics.install_crash_handlers(config.LOG_FILE)
        Diagnostics.log_qt_messages()

        log.debug("Создаю QApplication")
        from PySide6.QtCore import QTimer

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        container.qt_app.override(app)
        # кто и когда закрывает приложение — чтобы поймать неожиданный выход из цикла событий
        app.aboutToQuit.connect(lambda: log.warning("QApplication.aboutToQuit — приложение закрывается"))

        def _shutdown_ai() -> None:
            # на выходе из Капри гасим и ComfyUI, и локальную модель — чтобы не висели и не ели VRAM
            try:
                settings = container.command_context().settings
            except Exception:
                settings = {}
            if not settings.get("stop_ai_on_exit", True):
                return
            log.info("Выключаю ComfyUI и локальную модель вслед за Капри")
            try:
                container.image_generation_adapter().stop()
            except Exception:
                log.exception("ComfyUI не выключился при выходе")
            try:
                local = container.local_chat_adapter()
                if local:
                    local.stop_server()
            except Exception:
                log.exception("Локальная модель не выключилась при выходе")
            try:
                container.browser_automation_adapter().close()
            except Exception:
                log.exception("Браузер Капри не закрылся при выходе")

        app.aboutToQuit.connect(_shutdown_ai)

        # пульс: пока идёт в журнал — цикл событий жив; оборвался без «завершился» — процесс убили снаружи
        beat = {"n": 0}

        def heartbeat() -> None:
            beat["n"] += 1
            log.info("пульс %s — цикл событий жив", beat["n"])

        timer = QTimer()
        timer.timeout.connect(heartbeat)
        timer.start(3000)
        app._heartbeat_timer = timer  # держим ссылку, чтобы таймер не собрал сборщик мусора

        log.debug("Создаю сессию ассистента")
        session = container.assistant_session_usecase()
        log.debug("Показываю трей")
        container.tray_menu().show()
        log.debug("Запускаю сессию")
        session.start()
        log.info("Вхожу в цикл событий Qt (app.exec)")
        code = app.exec()
        log.warning("Цикл событий Qt завершился с кодом %s", code)
        sys.exit(code)

    def run(self) -> None:
        try:
            self._main()
        except SystemExit:
            raise
        except Exception as e:
            log.exception("Капри упала при запуске")
            Diagnostics.fatal(f"Что-то сломалось при запуске: {e}\n\nПодробности — в файле capri.log в папке Капри.")
