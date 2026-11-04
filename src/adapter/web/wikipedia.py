"""Краткая справка из русской Википедии для озвучки."""
import json
import logging
import re
import urllib.parse
import urllib.request

log = logging.getLogger("capri")


def wiki_summary(query, sentences=2):
    """Первые предложения статьи русской Википедии по запросу, подготовленные для озвучки. None — не нашлось."""
    headers = {"User-Agent": "CapriAssistant/1.0 (personal voice assistant)"}

    def get(url):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=6) as r:
            return json.loads(r.read().decode("utf-8"))
    try:
        found = get("https://ru.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=1&srsearch="
                    + urllib.parse.quote(query))["query"]["search"]
        if not found:
            return None
        page = get("https://ru.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(found[0]["title"].replace(" ", "_")))
    except Exception as e:
        log.info("Википедия недоступна: %s", e)
        return None
    if page.get("type") == "disambiguation":
        return None
    text = page.get("extract", "").replace("́", "")  # знаки ударения
    text = re.sub(r"\s*\([^()]*\)", "", text)       # транскрипции, даты и пр. в скобках — не для озвучки
    text = re.sub(r"\s*\[[^\]]*\]", "", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z])", text.strip())
    out = " ".join(parts[:sentences]).strip()
    if len(out) > 300:
        out = out[:300].rsplit(" ", 1)[0] + "…"
    return out or None
