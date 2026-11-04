from typing import Any

from src.adapter.llm.claude_chat_model import AI
from src.application.assistant.interfaces.i_chat_model_adapter import IChatModelAdapter


class ClaudeChatModelAdapter(IChatModelAdapter):
    """Claude (Anthropic API) с веб-поиском. Работает, только если в настройках есть ключ."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self._ai = AI(settings)

    @property
    def available(self) -> bool:
        return self._ai.available

    def ask(self, question: str) -> str | None:
        return self._ai.ask(question)

    def summarize_report(self, report: str) -> str | None:
        return self._ai.summarize_report(report)
