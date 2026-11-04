from src.adapter.web.wikipedia import wiki_summary
from src.application.assistant.interfaces.i_encyclopedia_adapter import IEncyclopediaAdapter


class WikipediaAdapter(IEncyclopediaAdapter):
    """Русская Википедия."""

    def summary(self, query: str, sentences: int = 2) -> str | None:
        return wiki_summary(query, sentences=sentences)
