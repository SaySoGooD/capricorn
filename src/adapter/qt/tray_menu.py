"""Значок Капри в трее и его меню (то же меню открывается правым кликом по Капри)."""
import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QSlider,
    QSystemTrayIcon,
    QWidget,
    QWidgetAction,
)

from src.adapter.qt.avatar_widget import Avatar
from src.application.assistant.command_context import CommandContext
from src.application.assistant.commands import CAPRI_URL
from src.application.assistant.interfaces.i_assistant_session_usecase import IAssistantSessionUseCase
from src.application.assistant.interfaces.i_open_url_usecase import IOpenUrlUseCase
from src.application.assistant.interfaces.i_remember_entry_usecase import IRememberEntryUseCase

log = logging.getLogger("capri")


def tray_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(255, 34, 96))
    p.setPen(QPen(QColor(150, 70, 255), 4))
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QColor(6, 24, 20))
    p.setPen(QPen(QColor(40, 255, 150), 4))
    p.drawEllipse(14, 22, 36, 20)
    p.setBrush(QColor(40, 255, 150))
    p.drawEllipse(27, 27, 10, 10)
    p.end()
    return QIcon(pm)


class TrayMenu:
    def __init__(
        self,
        app: QApplication,
        avatar: Avatar,
        session: IAssistantSessionUseCase,
        context: CommandContext,
        remember: IRememberEntryUseCase,
        open_url: IOpenUrlUseCase,
        settings_path: str,
    ) -> None:
        self._app = app
        self._avatar = avatar
        self._session = session
        self._context = context
        self._remember = remember
        self._open_url = open_url
        self._settings_path = settings_path
        self._windows = {}  # открытые окна держим, пока открыты (иначе их соберёт сборщик мусора)
        self.menu = QMenu()
        self.tray = QSystemTrayIcon(tray_icon())

    # ----- окна -----
    def _show_window(self, kind, make):
        old = self._windows.get(kind)
        if old is not None and old.isVisible():
            old.close()
        dlg = self._windows[kind] = make()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _ask_text(self):
        text, ok = QInputDialog.getText(None, "Капри", "Команда или вопрос:")
        if ok and text.strip():
            self._session.text_command(text.strip())

    def _open_entries(self):
        from src.adapter.qt.entries_dialog import EntriesDialog
        self._session.reload_settings_if_changed(speak=False)
        self._show_window("entries", lambda: EntriesDialog(self._context, self._remember))

    def _open_sound(self):
        from src.adapter.qt.sound_dialog import SoundDialog
        self._show_window("sound", lambda: SoundDialog(self._session))

    def _open_profile(self):
        from src.adapter.qt.profile_dialog import ProfileDialog
        self._show_window("profile", lambda: ProfileDialog(self._session))

    # ----- подменю -----
    def _add_mic_menu(self):
        session = self._session
        mic_menu = self.menu.addMenu("Микрофон")

        def fill_mics(m=mic_menu):
            """Список устройств ввода строится при каждом открытии — чтобы видеть только что подключённые."""
            m.clear()
            chosen = session.settings.get("mic_device")
            options = [(None, f"По умолчанию (как в Windows: {session.default_input_name()})")]
            try:
                options += [(n, n) for n in session.input_devices()]
            except Exception:
                log.exception("Не удалось получить список микрофонов")
            for value, label in options:
                a = QAction(label, m)
                a.setCheckable(True)
                a.setChecked(value == chosen or (value is None and not chosen))
                a.triggered.connect(lambda _=False, v=value: session.set_mic(v))
                m.addAction(a)
            m.addSeparator()
            tune = QAction("Громкость и чувствительность…", m)
            tune.triggered.connect(self._open_sound)
            m.addAction(tune)
        mic_menu.aboutToShow.connect(fill_mics)

    def _add_volume_menu(self):
        """«Громкость Капри» — ползунок прямо в меню, чтобы не лезть в микшер громкости Windows."""
        session = self._session
        vol_menu = self.menu.addMenu("Громкость Капри")
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(10, 6, 10, 6)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setMinimumWidth(180)
        value = QLabel()
        value.setMinimumWidth(36)
        row.addWidget(slider)
        row.addWidget(value)
        slider.valueChanged.connect(lambda v, lbl=value: lbl.setText(f"{v}%"))
        slider.sliderReleased.connect(lambda s=slider: session.set_voice_volume(s.value()))
        slider.valueChanged.connect(lambda v, s=slider: None if s.isSliderDown() else session.set_voice_volume(v))
        wa = QWidgetAction(vol_menu)
        wa.setDefaultWidget(box)
        vol_menu.addAction(wa)

        def sync_volume(s=slider, lbl=value):
            s.blockSignals(True)
            s.setValue(int(session.settings.get("voice_volume", 100)))
            s.blockSignals(False)
            lbl.setText(f"{s.value()}%")
        vol_menu.aboutToShow.connect(sync_volume)

    def _add_toggles(self):
        session = self._session
        # галочка: открывать ли Google, когда Капри не знает ответа (search_when_unsure)
        search_act = QAction("Искать в браузере, если не знаю", self.menu)
        search_act.setCheckable(True)
        search_act.toggled.connect(session.set_search_when_unsure)
        self.menu.addAction(search_act)
        # галочка: появляется ли Капри сама время от времени (chatter)
        chatter_act = QAction("Появляться самой", self.menu)
        chatter_act.setCheckable(True)
        chatter_act.toggled.connect(session.set_chatter)
        self.menu.addAction(chatter_act)

        def sync_search(a=search_act, b=chatter_act):
            session.reload_settings_if_changed(speak=False)  # могли поменять в config.json руками
            for act, key, default in ((a, "search_when_unsure", True), (b, "chatter", True)):
                act.blockSignals(True)
                act.setChecked(bool(session.settings.get(key, default)))
                act.blockSignals(False)
        self.menu.aboutToShow.connect(sync_search)

    def show(self) -> None:
        session = self._session
        for title, fn in (("Позвать Капри", session.call_from_click),
                          ("Замолчать", session.interrupt),
                          ("Написать команду…", self._ask_text),
                          ("Мои сайты, программы и ответы…", self._open_entries),
                          ("Как ко мне обращаться…", self._open_profile),
                          ("Проверить ПК", lambda: session.text_command("проверь компьютер")),
                          ("Спрятать", self._avatar.vanish),
                          ("MIC", None),
                          ("SEARCH", None),
                          ("Открыть config.json", lambda: os.startfile(self._settings_path)),
                          ("Капри на GitHub (обновления)…", lambda: self._open_url(CAPRI_URL)),
                          (None, None),
                          ("Выход", self._app.quit)):
            if title is None:
                self.menu.addSeparator()
            elif title == "MIC":
                self._add_mic_menu()
                self._add_volume_menu()
            elif title == "SEARCH":
                self._add_toggles()
            else:
                act = QAction(title, self.menu)
                act.triggered.connect(fn)
                self.menu.addAction(act)

        self.tray.setToolTip("Капри — голосовой ассистент")
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda r: session.call_from_click()
                                    if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()
        self._avatar.menu_requested.connect(lambda pos: self.menu.popup(pos))
        self._avatar.clicked.connect(session.call_from_click)
