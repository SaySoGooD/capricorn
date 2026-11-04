"""Запуск Капри: журнал, Qt, контейнер зависимостей, трей и сессия ассистента."""
import logging
import sys

from src.main.logging_setup import fatal, setup_logging

log = logging.getLogger("capri")


def main() -> None:
    # журнал — до всех библиотек: если какой-то не хватает, Капри падает без окна, и узнать причину можно только тут
    setup_logging()
    try:
        from PySide6.QtWidgets import QApplication

        from src.main.dependency_injection import container
    except ImportError as e:
        log.exception("Не хватает библиотек")
        fatal(f"Не установлены нужные библиотеки ({e.name or e}).\n\n"
              f"Запусти setup.bat в папке Капри и дождись надписи «Готово», потом снова run.bat.\n"
              f"Если setup.bat выдаёт ошибку — сфотографируй его окно.\n\nPython {sys.version.split()[0]}")
        return

    config = container.config()
    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    container.qt_app.override(app)

    session = container.assistant_session_usecase()
    container.tray_menu().show()
    session.start()
    sys.exit(app.exec())


def run() -> None:
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log.exception("Капри упала при запуске")
        fatal(f"Что-то сломалось при запуске: {e}\n\nПодробности — в файле capri.log в папке Капри.")
