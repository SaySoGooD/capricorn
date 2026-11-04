"""Разбор цепочек действий: «открой телеграм, первый чат, напиши привет»."""
import re

# ---------------- разбор цепочки ----------------

APP_WINDOWS = {  # как опознать окно приложения по заголовку
    "telegram": ("telegram",), "телеграм": ("telegram",), "телега": ("telegram",),
    "ютуб": ("youtube",), "youtube": ("youtube",),
    "блокнот": ("блокнот", "notepad"), "notepad": ("notepad", "блокнот"),
    "дискорд": ("discord",), "discord": ("discord",),
    "ватсап": ("whatsapp",), "whatsapp": ("whatsapp",),
    "вк": ("вконтакте", "vk"), "вконтакте": ("вконтакте", "vk"),
    "браузер": ("firefox", "chrome", "edge", "opera", "яндекс", "brave"),
}
TYPE_VERBS = r"напиши|напечатай|введи|набери|вбей|впиши|пиши"
NOT_TYPING = r"(стих\w*|стишок|рассказ\w*|истори\w*|сказк\w*|шутк\w*|анекдот\w*|песн\w*|сочинени\w*|эссе)\b"
ORDINALS = {"первый": 1, "первую": 1, "второй": 2, "вторую": 2, "третий": 3, "третью": 3, "четвертый": 4,
            "четвёртый": 4, "пятый": 5, "шестой": 6, "седьмой": 7, "восьмой": 8, "девятый": 9, "десятый": 10}
STEP_START = re.compile(
    r"\b(?<!нажми на )(?<!нажми )(?<!перейди )(?<!перейди в )(?<!поставь курсор в )"
    r"(?:и\s+|потом\s+|затем\s+|после\s+этого\s+)?"
    r"(?=(?:открой|запусти|зайди|перейди|нажми на поиск|нажми поиск|поиск|в поиск|найди|поищи|"
    r"прокрути|пролистай|листай|полистай|скролль|промотай страниц|"
    rf"{TYPE_VERBS}|отправь|(?:{'|'.join(ORDINALS)}) (?:чат|диалог|переписк)|"
    r"(?:в |открой )?(?:чат\w*|chat|диалог\w*|переписк\w*|контакт\w*) )\b)")


def split_chain(cmd):
    """«открой телеграм первый чат напиши привет» → ['открой телеграм', 'первый чат', 'напиши привет'].
    Всё после «напиши» — это текст (кроме хвоста «и отправь»). None — если шаг один."""
    c = cmd.strip()
    m = re.search(rf"\b({TYPE_VERBS})\b", c)
    head, tail = (c[:m.start()], c[m.start():]) if m else (c, "")
    parts = [p.strip(" ,.") for p in STEP_START.split(head) if p and p.strip(" ,.")]
    parts = [re.sub(r"\s+(и|потом|затем)$", "", re.sub(r"^(и|потом|затем|после этого)\s+", "", p))
             for p in parts]
    if tail:
        parts.append(tail.strip(" ,."))
    parts = [p for p in parts if p]
    merged = []
    for p in parts:
        # «найди в телеграм» / «зайди в телеграм» в начале цепочки = открыть Telegram
        p = re.sub(r"^(найди|зайди|перейди|открой)( в)? (телеграм\w*|telegram|телег\w*)$", "открой телеграм", p)
        if merged and (merged[-1] in ORDINALS or merged[-1] in ("открой", "зайди", "перейди", "найди", "зайди в",
                                                                 "перейди в", "открой мне")):
            merged[-1] = merged[-1] + " " + p  # «третий» + «чат», «открой» + «чат с мамой»
        else:
            merged.append(p)
    return merged if len(merged) >= 2 else None


def parse_type(step):
    """«напиши привет и отправь» → ('привет', True). None — если это не печать."""
    m = re.match(rf"^({TYPE_VERBS})\s+(?P<t>.+)$", step.strip())
    if not m:
        return None
    text = m.group("t").strip()
    if re.match(NOT_TYPING, text):
        return None
    # «напиши» — печатает и отправляет (Enter), «напечатай / введи / набери» — только печатает
    send = None if m.group(1) in ("напиши", "пиши", "впиши") else False
    end = re.search(r"\s+(и\s+)?(отправь|отправить|нажми энтер|нажми enter|и энтер)$", text)
    if end:
        text, send = text[:end.start()].strip(), True
    text = re.sub(r"^(текст|сообщение|фразу|слово)\s+", "", text)
    return text, send
