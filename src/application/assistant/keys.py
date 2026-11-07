"""Разбор сочетаний клавиш из речи: «вин таб», «контрол шифт эскейп», «эф пять»."""
import re

from src.application.assistant.text import Text


class Keys:
    """Разбор сочетаний клавиш из речи. Без состояния — методы статические, таблицы в атрибутах класса."""

    # названия клавиш, которые понимает клавиатура (коды — в адаптере Windows)
    KEY_NAMES = {"win", "ctrl", "alt", "shift", "tab", "enter", "esc", "space", "backspace", "delete", "insert",
                 "home", "end", "pageup", "pagedown", "left", "up", "right", "down", "printscreen", "capslock",
                 "menu"}

    KEY_WORDS = {  # как клавиши произносят (Vosk пишет кириллицей, Google — часто латиницей)
        "win": "вин винд винда виндовс виндоус виндоуз виндос виндус виндо windows window win wind винды "
               "виндоуса виндовса",
        "ctrl": "контрол контроль контрл кнтрл ктрл контр ctrl control ctl",
        "alt": "альт алт alt", "shift": "шифт shift", "tab": "таб табуляция tab",
        "enter": "энтер ентер enter ввод return", "esc": "эскейп искейп эскейф эск esc escape",
        "space": "пробел space спейс", "backspace": "бэкспейс бекспейс backspace",
        "delete": "делит дилит делейт delete del дел", "insert": "инсерт insert", "home": "хоум home",
        "end": "энд end", "printscreen": "принтскрин printscreen prtsc", "capslock": "капслок capslock",
        "left": "влево лево налево left", "right": "вправо право направо right",
        "up": "вверх наверх up", "down": "вниз down", "menu": "меню",
    }
    WORD_TO_KEY = {w: k for k, ws in KEY_WORDS.items() for w in ws.split()}
    LETTER_NAMES = {"эй": "a", "би": "b", "си": "c", "ди": "d", "и": "e", "эф": "f", "джи": "g", "эйч": "h",
                    "ай": "i", "джей": "j", "кей": "k", "эл": "l", "эм": "m", "эн": "n", "оу": "o", "пи": "p",
                    "кью": "q", "ар": "r", "эс": "s", "ти": "t", "ю": "u", "ви": "v", "дабл ю": "w",
                    "дабл-ю": "w", "экс": "x", "икс": "x", "уай": "y", "игрек": "y", "зед": "z", "зет": "z",
                    # по-русски: «контрол цэ», «вин дэ», и одиночные буквы «вин д»
                    "а": "a", "бэ": "b", "б": "b", "цэ": "c", "ц": "c", "дэ": "d", "д": "d", "е": "e",
                    "гэ": "g", "г": "g", "ха": "h", "ка": "k", "к": "k", "эль": "l", "л": "l", "м": "m",
                    "н": "n", "о": "o", "пэ": "p", "п": "p", "эр": "r", "р": "r", "с": "s", "тэ": "t", "т": "t",
                    "у": "u", "вэ": "v", "в": "v", "зэ": "z", "з": "z"}
    SKIP_WORDS_KEYS = {"и", "плюс", "кнопку", "кнопка", "кнопки", "клавишу", "клавиши", "клавиша", "клавиш",
                       "сочетание", "сочетания", "комбинацию", "комбинация", "стрелку", "стрелка", "стрелочку",
                       "на", "клавиатуре", "одновременно", "мне", "пожалуйста", "plus", "and"}

    @staticmethod
    def split_glued(word):
        """Google иногда склеивает сочетание в одно слово: «wintab», «альттаб», «ctrlshiftesc».
        Режем на известные названия клавиш (одиночная буква/цифра допустима только последней)."""
        names = sorted((w for w in Keys.WORD_TO_KEY if len(w) > 1), key=len, reverse=True)

        def go(rest):
            if not rest:
                return []
            for n in names:
                if rest.startswith(n):
                    tail = go(rest[len(n):])
                    if tail is not None:
                        return [Keys.WORD_TO_KEY[n]] + tail
            f = re.match(r"[fф](1[0-2]|[1-9])", rest)
            if f:
                tail = go(rest[f.end():])
                if tail is not None:
                    return ["f" + f.group(1)] + tail
            if len(rest) == 1 and re.fullmatch(r"[a-z0-9]", rest):
                return [rest]
            return None
        return go(word)

    @staticmethod
    def parse_keys(text):
        """«вин таб» / «ctrl shift esc» / «эф пять» → ['win', 'tab'] ... Возвращает (клавиши, нераспознанное)."""
        t = re.sub(r"[+\-_,.]", " ", Text.norm(text))
        for a, b in (("пейдж ап", "pageup"), ("page up", "pageup"), ("пейдж даун", "pagedown"),
                     ("page down", "pagedown"), ("принт скрин", "printscreen"), ("print screen", "printscreen"),
                     ("капс лок", "capslock"), ("caps lock", "capslock"), ("дабл ю", "дабл-ю"),
                     ("бэк спейс", "backspace"), ("back space", "backspace")):
            t = t.replace(a, b)
        words = t.split()
        keys, i = [], 0
        while i < len(words):
            w = words[i]
            nxt = words[i + 1] if i + 1 < len(words) else ""
            if w in Keys.WORD_TO_KEY or w in Keys.KEY_NAMES:
                keys.append(Keys.WORD_TO_KEY.get(w, w))
            elif re.fullmatch(r"[fф]\d{1,2}", w):
                keys.append("f" + w[1:])
            elif w in ("эф", "ф", "f") and (nxt.isdigit() or nxt in Text.NUM):
                keys.append(f"f{int(nxt) if nxt.isdigit() else Text.NUM[nxt]}")
                i += 1
            elif w in Keys.LETTER_NAMES and not (w == "и" and keys and i + 1 < len(words)):
                keys.append(Keys.LETTER_NAMES[w])
            elif re.fullmatch(r"[a-z0-9]", w):
                keys.append(w)
            elif w in Text.NUM and Text.NUM[w] < 10:
                keys.append(str(Text.NUM[w]))
            elif w not in Keys.SKIP_WORDS_KEYS:
                glued = Keys.split_glued(w)
                if not glued:
                    return [], w
                keys += glued
            i += 1
        return keys, None
