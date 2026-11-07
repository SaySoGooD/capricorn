"""Капри отвечает о себе по собственному коду. Вопрос → семантический поиск по её исходникам (RAG) →
локальная модель объясняет СТРОГО по найденным кускам. Если в коде ответа нет — честно говорит, что не
нашла, и не выдумывает."""
import logging
import re
import threading

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_code_rag_adapter import ICodeRagAdapter
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.interfaces.i_self_knowledge_usecase import ISelfKnowledgeUseCase
from src.application.assistant.persona import persona

log = logging.getLogger("capri")

# Строгий грунтованный промпт: отвечать только по приложенному коду, иначе — «не нашла».
GROUND_SYSTEM = (
    persona.CHARACTER + "\n\n" + persona.SPEECH_RULES +
    "\n\nНиже приложены куски твоего СОБСТВЕННОГО исходного кода (Python). Это единственный источник. "
    "Ответь на вопрос пользователя о себе, опираясь ТОЛЬКО на этот код, своими словами и по делу. "
    "Объясняй смысл (что ты умеешь и как это устроено), а не цитируй строки и не показывай сам код. "
    "Если в приложенных кусках ответа нет — прямо скажи, что не нашла этого у себя, и НИЧЕГО не выдумывай."
)
MAX_CONTEXT = 6000  # символов кода в промпт, чтобы не переполнить контекст 35B


class SelfKnowledgeUseCase(ISelfKnowledgeUseCase):
    def __init__(
        self,
        context: CommandContext,
        rag: ICodeRagAdapter,
        local_chat: ILocalChatModelAdapter | None = None,
    ) -> None:
        self._context = context
        self._rag = rag
        self._local = local_chat
        self._build_thread: threading.Thread | None = None

    def ensure_index(self) -> None:
        """Построить индекс в фоне, если ещё не готов (зовётся при старте и при первом вопросе)."""
        if not self._context.settings.get("self_rag", True):
            return
        if self._rag.is_ready() or (self._build_thread and self._build_thread.is_alive()):
            return
        self._build_thread = threading.Thread(target=self._rag.build, daemon=True, name="rag-build")
        self._build_thread.start()

    def explain(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._context.settings.get("self_rag", True):
            return ReplyDTO(persona.line("self_rag_off"))
        if not self._rag.is_ready():
            self.ensure_index()
            return ReplyDTO(persona.line("self_building"))
        query = (m.groupdict().get("q") or c).strip(" .,!?:;«»\"'")
        k = int(self._context.settings.get("rag_top_k", 5))
        hits = self._rag.search(query, k=k)
        if not hits:
            return ReplyDTO(persona.line("self_unknown"))
        if not (self._local and self._local.available):
            return ReplyDTO(persona.line("self_offline"))
        context = ""
        for h in hits:
            piece = "# %s (строка %d)\n%s\n\n" % (h["file"], h["start"], h["text"])
            if len(context) + len(piece) > MAX_CONTEXT:
                break
            context += piece
        log.info("RAG: вопрос о себе %r → %s", query, [h["file"] for h in hits])
        answer = self._local.instruct(GROUND_SYSTEM + "\n\nКОД:\n" + context, query)
        return ReplyDTO(answer or persona.line("self_unknown"), "answer")

    def rag_info(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._context.settings.get("self_rag", True):
            return ReplyDTO(persona.line("self_rag_off"))
        if not self._rag.is_ready():
            self.ensure_index()
            return ReplyDTO(persona.line("self_building"))
        st = self._rag.stats()
        mods = ", ".join(st["modules"][:8]) or "свой код"
        return ReplyDTO("В моей памяти проиндексировано %d кусков из %d файлов. Вижу свои модули: %s. "
                        "Спрашивай, как у меня что устроено." % (st["chunks"], st["files"], mods), "answer")
