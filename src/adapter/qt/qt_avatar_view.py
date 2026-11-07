"""Экранная Капри через Qt: вызовы из любых потоков доходят до окна сигналами (в потоке интерфейса)."""
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from src.adapter.qt.avatar_widget import Avatar
from src.application.assistant.interfaces.i_avatar_view import IAvatarView


class _Signals(QObject):
    summon = Signal()
    vanish = Signal()
    mode = Signal(str, float)
    subtitle = Signal(str)
    quit_app = Signal()
    anim = Signal(str)
    roam = Signal()
    hop = Signal()
    move_to = Signal(str)
    boot_start = Signal()
    boot_text = Signal(str)
    boot_end = Signal()
    launch_flash = Signal()


class QtAvatarView(IAvatarView):
    def __init__(self, avatar: Avatar, app: QApplication) -> None:
        self.avatar = avatar
        s = self._signals = _Signals()
        s.summon.connect(avatar.summon)
        s.vanish.connect(avatar.vanish)
        s.mode.connect(avatar.set_mode)
        s.subtitle.connect(avatar.set_subtitle)
        s.quit_app.connect(app.quit)
        s.anim.connect(avatar.play_anim)
        s.roam.connect(avatar.start_roam)
        s.hop.connect(avatar.start_hopping)
        s.move_to.connect(avatar.move_to_named)
        s.boot_start.connect(avatar.start_boot)
        s.boot_text.connect(avatar.set_boot_text)
        s.boot_end.connect(avatar.end_boot)
        s.launch_flash.connect(avatar.launch_flash)

    def launch_effect(self) -> None:
        self._signals.launch_flash.emit()

    def start_boot(self) -> None:
        self._signals.boot_start.emit()

    def set_boot(self, text: str) -> None:
        self._signals.boot_text.emit(text)

    def end_boot(self) -> None:
        self._signals.boot_end.emit()

    def summon(self) -> None:
        self._signals.summon.emit()

    def vanish(self) -> None:
        self._signals.vanish.emit()

    def set_mode(self, mode: str, seconds: float = 0.0) -> None:
        self._signals.mode.emit(mode, float(seconds))

    def set_subtitle(self, text: str) -> None:
        self._signals.subtitle.emit(text)

    def play_anim(self, name: str) -> None:
        self._signals.anim.emit(name)

    def roam(self) -> None:
        self._signals.roam.emit()

    def hop(self) -> None:
        self._signals.hop.emit()

    def move_to(self, where: str) -> None:
        self._signals.move_to.emit(where)

    def quit_app(self) -> None:
        self._signals.quit_app.emit()
