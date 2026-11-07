"""Эмбеддинги через fastembed (ONNX, CPU) — без torch и без видеопамяти, чтобы не мешать 35B.

Модель скачивается один раз при первом обращении (интернет нужен только тогда). Если библиотека не
установлена или модель не загрузилась — адаптер просто сообщает available=False, и RAG отключается мягко."""
import logging
import threading
from typing import Any

from src.application.assistant.interfaces.i_embedding_adapter import IEmbeddingAdapter

log = logging.getLogger("capri")

# многоязычная модель: хорошо понимает русские вопросы и латиницу кода, маленькая (384 измерения)
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class FastEmbedAdapter(IEmbeddingAdapter):
    def __init__(self, settings: dict[str, Any]) -> None:
        self._model_name = str(settings.get("embedding_model") or DEFAULT_MODEL)
        self._model = None
        self._failed = False
        self._lock = threading.Lock()

    def _ensure(self):
        if self._model is not None or self._failed:
            return self._model
        with self._lock:
            if self._model is not None or self._failed:
                return self._model
            try:
                from fastembed import TextEmbedding
                log.info("Загружаю модель эмбеддингов %s (CPU)…", self._model_name)
                self._model = TextEmbedding(model_name=self._model_name)
                log.info("Модель эмбеддингов готова")
            except Exception as e:
                log.warning("Эмбеддинги недоступны (%s): %s", self._model_name, e)
                self._failed = True
            return self._model

    @property
    def available(self) -> bool:
        return self._ensure() is not None

    def embed(self, texts: list[str]) -> list[Any] | None:
        model = self._ensure()
        if model is None:
            return None
        try:
            import numpy as np
            return [np.asarray(v, dtype=np.float32) for v in model.embed(list(texts))]
        except Exception as e:
            log.warning("Не удалось посчитать эмбеддинги: %s", e)
            return None
