from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ListenerCallbacksDTO:
    """Куда слушатель микрофона отдаёт события (вызываются из его потока)."""

    on_final: Callable[[str, bytes], None]
    on_partial: Callable[[str], None]
    on_error: Callable[..., None]
