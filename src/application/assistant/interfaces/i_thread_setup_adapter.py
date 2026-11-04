from abc import ABC, abstractmethod


class IThreadSetupAdapter(ABC):
    """Подготовка рабочего потока к вызовам системы (на Windows — COM для звука и UI Automation)."""

    @abstractmethod
    def prepare_worker_thread(self) -> None: ...
