"""Разбор времени из речи для перемотки: «на 3:14», «с двадцать седьмой минуты», «на полминуты»."""
import re

from src.application.assistant.text import Text


class MediaTime:
    """Разбор и форматирование времени из речи. Без состояния — методы статические."""

    ORDINALS = [  # корень порядкового числа → количественное («двадцать седьмой минуты» → «двадцать семь»)
        ("одиннадцат", "одиннадцать"), ("двенадцат", "двенадцать"), ("тринадцат", "тринадцать"),
        ("четырнадцат", "четырнадцать"), ("пятнадцат", "пятнадцать"), ("шестнадцат", "шестнадцать"),
        ("семнадцат", "семнадцать"), ("восемнадцат", "восемнадцать"), ("девятнадцат", "девятнадцать"),
        ("двадцат", "двадцать"), ("тридцат", "тридцать"), ("сороков", "сорок"), ("пятидесят", "пятьдесят"),
        ("шестидесят", "шестьдесят"), ("семидесят", "семьдесят"), ("восьмидесят", "восемьдесят"),
        ("девяност", "девяносто"), ("сот", "сто"),
        ("перв", "один"), ("втор", "два"), ("трет", "три"), ("четверт", "четыре"), ("пят", "пять"),
        ("шест", "шесть"), ("седьм", "семь"), ("восьм", "восемь"), ("девят", "девять"), ("десят", "десять"),
    ]
    ORD_END = r"(ой|ая|ую|ый|ий|ей|ья|ье|ого|ому|ом|ым|ые|ых|ьей|ьего|ьим)"

    @staticmethod
    def _num(text):
        return Text.parse_number(text)

    @staticmethod
    def ordinals_to_cardinals(t):
        """«с двадцать седьмой минуты» → «с двадцать семь минуты», «с 27-й минуты» → «с 27 минуты»."""
        t = re.sub(r"(\d+)-?(й|я|ю|ой|ая|ую|ий|ей|го|ого)\b", r"\1", t)
        words = []
        for w in t.split():
            for stem, card in MediaTime.ORDINALS:
                if re.fullmatch(stem + MediaTime.ORD_END, w):
                    w = card
                    break
            words.append(w)
        return " ".join(words)

    @staticmethod
    def parse_time(text):
        """«3:14», «1:02:03», «3 минуты 14 секунд», «на две минуты», «полминуты», «на начало» → секунды."""
        t = MediaTime.ordinals_to_cardinals(text.lower().replace("ё", "е"))
        if re.search(r"\bнача\w*|\bсначала\b|\bзаново\b", t):
            return 0
        m = re.search(r"(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?", t)
        if m:
            a, b, c = int(m.group(1)), int(m.group(2)), m.group(3)
            return a * 3600 + b * 60 + int(c) if c else a * 60 + b
        if "полминут" in t:
            return 30
        if "полторы минут" in t:
            return 90
        total, found = 0, False
        for unit, mult in ((r"час\w*", 3600), (r"минут\w*", 60), (r"секунд\w*|сек\b", 1)):
            um = re.search(rf"(?:(\S+(?:\s+\S+)?)\s+)?(?:{unit})", t)
            if um:
                before = um.group(1) or ""
                n = None
                # число прямо перед единицей: «3 минуты», «двадцать пять секунд», «минуту» (= 1)
                words = before.split()
                for k in (2, 1):
                    if len(words) >= k:
                        n = MediaTime._num(" ".join(words[-k:]))
                        if n is not None:
                            break
                total += (n if n is not None else 1) * mult
                found = True
        if found:
            return total
        nums = MediaTime.number_groups(t)
        if len(nums) == 2:  # «поставь на 3 14», «три четырнадцать» — минуты и секунды
            return nums[0] * 60 + nums[1]
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if nums and nums[0] >= 100 and nums[0] % 100 < 60:  # «тайминг 314» → 3:14, «1205» → 12:05
            return nums[0] // 100 * 60 + nums[0] % 100
        return nums[0] if nums else None  # одно число без единиц — секунды

    @staticmethod
    def number_groups(t):
        """Отдельные числа в тексте: «три четырнадцать» → [3, 14], «двадцать пять» → [25], «3 14» → [3, 14]."""
        out, tens = [], None
        for w in MediaTime.ordinals_to_cardinals(t).split():
            if w.isdigit():
                out.append(int(w))
                tens = None
            elif w in Text.NUM:
                v = Text.NUM[w]
                if tens is not None and 1 <= v <= 9:  # «двадцать» + «пять»
                    out[-1] += v
                    tens = None
                else:
                    out.append(v)
                    tens = v if v in (20, 30, 40, 50, 60, 70, 80, 90) else None
            else:
                tens = None
        return out

    @staticmethod
    def fmt(seconds):
        seconds = int(round(seconds))
        h, rest = divmod(seconds, 3600)
        m, s = divmod(rest, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
