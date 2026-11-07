from collections.abc import Callable
from typing import Any

from src.adapter.llm.ollama_chat_model import LocalAI
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter


class OllamaChatModelAdapter(ILocalChatModelAdapter):
    """Локальная нейросеть через Ollama — без ключа и интернета."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self._local = LocalAI(settings)

    @property
    def available(self) -> bool:
        return True

    def ask(self, question: str) -> str | None:
        return self._local.ask(question)

    def instruct(self, system: str, user: str) -> str | None:
        return self._local.instruct(system, user)

    def summarize_report(self, report: str) -> str | None:
        return self._local.summarize_report(report)

    def start_server(self) -> None:
        self._local.start_server()

    def stop_server(self) -> None:
        self._local.stop_server()

    def chatter(self) -> str | None:
        return self._local.chatter()

    def set_on_model_change(self, callback: Callable[[str], None]) -> None:
        self._local.on_model_change = callback
