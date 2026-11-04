import ctypes
import subprocess

from src.adapter.windows.powershell import NO_WINDOW
from src.application.assistant.interfaces.i_power_adapter import IPowerAdapter


class WindowsPowerAdapter(IPowerAdapter):
    def shutdown(self, restart: bool) -> None:
        subprocess.Popen(["shutdown", "/r" if restart else "/s", "/t", "10"], creationflags=NO_WINDOW)

    def lock(self) -> None:
        ctypes.windll.user32.LockWorkStation()
