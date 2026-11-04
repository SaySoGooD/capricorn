"""Как браузеры называют вслух и по каким именам процессов их узнавать."""
import re

# как браузеры называют вслух → по чему узнать в списке браузеров Windows (название ключа или exe)
BROWSER_WORDS = [
    (r"(гугл )?хром\w*|chrome", "chrome"),
    (r"яндекс\w*|yandex", "yandex"),
    (r"опер\w*|opera", "opera"),
    (r"(фаер|файр|файер)фокс\w*|мозил+\w*|firefox", "firefox"),
    (r"(майкрософт )?эдж\w*|edge", "edge"),
    (r"брейв\w*|brave", "brave"),
    (r"вивальди|vivaldi", "vivaldi"),
]
BROWSER_NAMES = {"chrome": "Google Chrome", "yandex": "Яндекс Браузер", "opera": "Opera", "firefox": "Firefox",
                 "edge": "Edge", "brave": "Brave", "vivaldi": "Vivaldi"}
# «… в хроме», «… через яндекс браузер», «… в браузере опера» — только в конце фразы
BROWSER_SUFFIX = re.compile(r"\s+(в|через)\s+(браузер\w*\s+)?(?P<b>" + "|".join(p for p, _ in BROWSER_WORDS)
                            + r")(\s+браузер\w*)?$")


# ---------------- ютуб ----------------

BROWSERS = ("firefox", "chrome", "msedge", "opera", "browser", "brave", "vivaldi", "yandex")
