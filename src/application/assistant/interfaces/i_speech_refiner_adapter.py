from abc import ABC, abstractmethod


class ISpeechRefinerAdapter(ABC):
    """Повторное, более точное распознавание уже записанной фразы."""

    @abstractmethod
    def refine(self, audio: bytes) -> str | None: ...
