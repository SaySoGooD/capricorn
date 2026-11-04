from abc import ABC, abstractmethod


class IAudioDevicesAdapter(ABC):
    @abstractmethod
    def input_devices(self) -> list[str]:
        """Названия микрофонов — по одному на устройство, как в настройках звука Windows."""
        ...

    @abstractmethod
    def default_input_name(self) -> str: ...
