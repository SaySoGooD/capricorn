from abc import ABC, abstractmethod


class IImageGenerationAdapter(ABC):
    """Генерация картинок по текстовому описанию (на Windows — локальный ComfyUI)."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Сервер генерации отвечает и готов рисовать."""
        ...

    @abstractmethod
    def generate(self, prompt: str, positive: str | None = None) -> str | None:
        """Нарисовать картинку. positive — готовый положительный промпт (если None, собирается из настроек).
        Путь к сохранённому PNG или None, если не вышло."""
        ...

    def start(self, timeout: float = 90.0) -> bool:
        """Поднять сервер генерации, если он не запущен. True — когда готов (по умолчанию просто проверка)."""
        return self.available

    def stop(self) -> None:
        """Остановить сервер генерации и освободить видеопамять (по умолчанию ничего не делает)."""
        return

    def free_vram(self) -> None:
        """Выгрузить свои модели из видеопамяти (по умолчанию ничего не делает)."""
        return
