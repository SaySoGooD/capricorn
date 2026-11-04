"""Установленные браузеры из реестра Windows."""
import os
import re

from src.application.assistant.browsers import BROWSER_WORDS
from src.application.assistant.text import norm


def installed_browsers():
    """{"chrome": путь к exe, ...} — браузеры из списка Windows («Приложения по умолчанию»)."""
    import winreg
    found = {}
    for hive, path in ((winreg.HKEY_CURRENT_USER, r"SOFTWARE\Clients\StartMenuInternet"),
                       (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Clients\StartMenuInternet"),
                       (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Clients\StartMenuInternet")):
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(key)[0]):
            name = winreg.EnumKey(key, i)
            try:
                cmd = winreg.QueryValue(key, name + r"\shell\open\command")
            except OSError:
                continue
            m = re.match(r'^\s*"?([^"]+?\.exe)', cmd)
            if not m or not os.path.isfile(m.group(1)):
                continue
            label = (name + " " + os.path.basename(m.group(1))).lower()
            for _, k in BROWSER_WORDS:
                if k in label or (k == "edge" and "msedge" in label):
                    found.setdefault(k, m.group(1))
    return found


def find_browser(name):
    """«хром» / «яндекс браузер» / путь к exe → путь к exe браузера или None, если такого нет."""
    if not name:
        return None
    if os.path.isfile(name):
        return name
    n = norm(name)
    for pattern, k in BROWSER_WORDS:
        if re.fullmatch(rf"({pattern})( браузер\w*)?|браузер\w* ({pattern})", n):
            return installed_browsers().get(k)
    return None
