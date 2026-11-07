"""Созвучные названия из речи: «роблокс» = «roblox», «клод» ~ «claude», но «запрет» ≠ «aseprite»."""
import re

from src.application.assistant.text import Text


class Fuzzy:
    """Сравнение названий «на слух». Без состояния — методы статические."""

    @staticmethod
    def sound(s: str) -> str:
        """Латиница «на слух»: без пробелов, c/q → k, w → v и т.п."""
        s = re.sub(r"\s", "", Text.translit(s.lower()))
        for a, b in (("ph", "f"), ("ck", "k"), ("c", "k"), ("q", "k"), ("w", "v"), ("x", "ks"), ("z", "s")):
            s = s.replace(a, b)
        return s

    @staticmethod
    def skeleton(s: str) -> str:
        """Согласные без гласных: «cloud», «claude», «клод» → «kld». Ловит созвучные названия."""
        return re.sub(r"[aeiouy]", "", Fuzzy.sound(s))

    @staticmethod
    def sounds_like(a: str, b: str) -> bool:
        """Созвучны, если совпадают согласные и первый звук."""
        sk = Fuzzy.skeleton(a)
        return len(sk) >= 3 and sk == Fuzzy.skeleton(b) and Fuzzy.sound(a)[:1] == Fuzzy.sound(b)[:1]
