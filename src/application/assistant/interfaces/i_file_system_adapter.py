from abc import ABC, abstractmethod

from src.application.assistant.dto.folder_dto import FolderDTO


class IFileSystemAdapter(ABC):
    @abstractmethod
    def find_folder(self, name: str, search: bool = False) -> FolderDTO | None:
        """Папка или диск по названию из речи; search=True — искать и среди своих папок."""
        ...

    @abstractmethod
    def known_dir(self, key: str) -> str:
        """desktop / documents / downloads / pictures / music / videos / screenshots."""
        ...

    @abstractmethod
    def open_path(self, path: str) -> None: ...

    @abstractmethod
    def create(self, folder: str, name: str, ext: str, is_folder: bool) -> str:
        """Создать папку или пустой файл, ничего не перезаписывая. Возвращает путь."""
        ...

    @abstractmethod
    def save_report(self, text: str) -> str:
        """Сохранить отчёт диагностики и вернуть путь к файлу."""
        ...
