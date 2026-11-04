from dataclasses import dataclass


@dataclass(frozen=True)
class FolderDTO:
    """Папка или диск: путь (или shell:-путь) и как назвать её вслух."""

    path: str
    label: str
