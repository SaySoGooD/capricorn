import logging
import re
import threading

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_file_system_adapter import IFileSystemAdapter
from src.application.assistant.interfaces.i_image_generation_adapter import IImageGenerationAdapter
from src.application.assistant.interfaces.i_image_generation_usecase import IImageGenerationUseCase
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.persona import persona

log = logging.getLogger("capri")

# Инструкция локальной модели: превратить описание в англоязычные booru-теги для SDXL/Pony.
TAG_SYSTEM = (
    "Ты — ассистент для генерации изображений в Stable Diffusion (модели SDXL и Pony). "
    "Пользователь даёт короткое описание на русском. Преврати его в положительный промпт — "
    "список англоязычных booru-тегов через запятую: субъект, его вид и действие, одежда, фон, "
    "освещение, ракурс, художественные детали. Пиши только теги через запятую, латиницей, "
    "в нижнем регистре, без предложений, без пояснений, без кавычек и без точки в конце. "
    "Не добавляй теги качества (score_9, masterpiece, best quality) — они уже подставляются отдельно."
)


class ImageGenerationUseCase(IImageGenerationUseCase):
    """Картинки через ComfyUI. Понимает «нарисуй/сгенерируй …», «запусти ComfyUI», «выгрузи ComfyUI».

    На «нарисуй …»: пока локальная LLM в памяти — она подбирает booru-теги по описанию, затем LLM
    выгружается из VRAM (35B и SDXL вместе не влезают в 16 ГБ), ComfyUI рисует, отдаёт память и LLM
    поднимается обратно. Подбор тегов — настройка comfyui_llm_tags, разгрузка LLM — pause_llm_on_draw."""

    def __init__(
        self,
        context: CommandContext,
        image: IImageGenerationAdapter,
        file_system: IFileSystemAdapter,
        local_chat: ILocalChatModelAdapter | None = None,
    ) -> None:
        self._context = context
        self._image = image
        self._files = file_system
        self._local = local_chat

    # ----- команды управления сервером -----
    def start_server(self, c: str, m: re.Match) -> ReplyDTO:
        if self._image.available:
            return ReplyDTO(persona.line("comfy_already"))
        ok = self._image.start()
        return ReplyDTO(persona.line("comfy_started" if ok else "comfy_start_fail"))

    def stop_server(self, c: str, m: re.Match) -> ReplyDTO:
        running = self._image.available
        self._image.stop()
        self._resume_llm()   # ComfyUI выключен — VRAM свободна, возвращаю LLM для разговора
        return ReplyDTO(persona.line("comfy_stopped" if running else "comfy_not_running"))

    # ----- рисование -----
    def draw(self, c: str, m: re.Match) -> ReplyDTO:
        if not self._context.settings.get("image_ai", True):
            return ReplyDTO(persona.line("draw_disabled"))
        if not self._image.available and not self._image.start():  # сам подниму ComfyUI, если не запущен
            return ReplyDTO(persona.line("draw_offline"))
        prompt = m.group("q").strip(" .,!?:;«»\"'")
        if not prompt:
            return ReplyDTO(persona.line("draw_fail"))
        positive = self._tags(prompt)   # теги подбираем, пока LLM ещё в памяти
        # LLM полностью выключается и отдаёт всю VRAM ComfyUI. Обратно НЕ поднимаем: ComfyUI остаётся
        # загруженным для следующих рисунков, а LLM вернётся, когда скажешь «выгрузи ComfyUI».
        self._pause_llm()
        path = self._image.generate(prompt, positive=positive)
        if not path:
            return ReplyDTO(persona.line("draw_fail"))
        try:
            self._files.open_path(path)
        except Exception:
            log.exception("Не удалось открыть нарисованную картинку")
        return ReplyDTO(persona.line("drawn", q=prompt))

    def _tags(self, prompt: str) -> str | None:
        """Пусть локальная модель подберёт booru-теги по описанию. None — если выключено/недоступно."""
        if not self._context.settings.get("comfyui_llm_tags", True):
            return None
        if not (self._local and self._local.available):
            return None
        tags = self._local.instruct(TAG_SYSTEM, prompt)
        if not tags:
            return None
        tags = re.sub(r'["«»\n]+', " ", tags).strip().strip("., ")
        if not tags:
            return None
        prefix = str(self._context.settings.get("comfyui_prompt_prefix", ""))
        log.info("LLM подобрала теги: %s", tags)
        return prefix + tags

    def _pause_llm(self) -> bool:
        if not self._context.settings.get("pause_llm_on_draw", True):
            return False
        if not (self._local and self._local.available):
            return False
        try:
            self._local.stop_server()
            return True
        except Exception:
            log.exception("Не удалось выгрузить локальную модель перед рисованием")
            return False

    def _resume_llm(self) -> None:
        if self._local:
            threading.Thread(target=self._local.start_server, daemon=True, name="llm-resume").start()
