"""Первое видео из поиска YouTube (без API-ключа, по странице результатов)."""
import json
import logging
import re
import urllib.parse
import urllib.request

log = logging.getLogger("capri")


def youtube_first(query):
    """(id, название) первого обычного видео (не шортс) в поиске YouTube или None."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as e:
        log.info("Поиск на YouTube не удался: %s", e)
        return None
    m = re.search(r'"videoRenderer":\{"videoId":"([\w-]{11})"', page)
    if not m:
        return None
    title = ""
    t = re.search(r'"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"', page[m.end():m.end() + 6000])
    if t:
        try:
            title = json.loads(f'"{t.group(1)}"')
        except ValueError:
            title = t.group(1)
    return m.group(1), title
