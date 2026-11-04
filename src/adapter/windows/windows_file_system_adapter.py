import datetime
import os

from src.adapter.windows.file_system import find_folder, known_dir
from src.application.assistant.dto.folder_dto import FolderDTO
from src.application.assistant.interfaces.i_file_system_adapter import IFileSystemAdapter


class WindowsFileSystemAdapter(IFileSystemAdapter):
    def __init__(self, reports_dir: str) -> None:
        self._reports_dir = reports_dir

    def find_folder(self, name: str, search: bool = False) -> FolderDTO | None:
        found = find_folder(name, search=search)
        return FolderDTO(path=found[0], label=found[1]) if found else None

    def known_dir(self, key: str) -> str:
        return known_dir(key)

    def open_path(self, path: str) -> None:
        os.startfile(path)

    def create(self, folder: str, name: str, ext: str, is_folder: bool) -> str:
        path = os.path.join(folder, name + ext)
        n = 2
        while os.path.exists(path):  # ничего не перезаписываем
            path = os.path.join(folder, f"{name} ({n}){ext}")
            n += 1
        if is_folder:
            os.makedirs(path)
        else:
            open(path, "x", encoding="utf-8").close()  # пустые .docx/.xlsx Office открывает как новые
        return path

    def save_report(self, text: str) -> str:
        os.makedirs(self._reports_dir, exist_ok=True)
        path = os.path.join(self._reports_dir, f"report_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path
