"""Пользовательские настройки в config.json: читаются поверх стандартных и меняются точечно."""
import json
import logging
import os
from collections.abc import Callable
from typing import Any

from src.application.assistant.default_settings import DEFAULTS
from src.application.assistant.dto.settings_dto import SettingsLoadResultDTO
from src.application.assistant.interfaces.i_settings_store import ISettingsStore

log = logging.getLogger("capri")


class JsonSettingsStore(ISettingsStore):
    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    def _blank(self) -> bool:
        """config.json нет или он пустой (всё стёрли) — такой можно спокойно создать заново."""
        try:
            with open(self._path, encoding="utf-8-sig") as f:
                return not f.read().strip()
        except FileNotFoundError:
            return True

    def _edit(self, change: Callable[[dict[str, Any]], Any]) -> str | None:
        """Прочитать config.json, применить change(data) и записать. Файл с ошибкой не перезаписываем —
        иначе пропадут правки пользователя. Возвращает текст ошибки или None."""
        try:
            if self._blank():
                data: dict[str, Any] = {}
            else:
                with open(self._path, encoding="utf-8-sig") as f:  # Блокнот иногда сохраняет с BOM
                    data = json.load(f)
        except Exception:
            log.exception("config.json с ошибкой, не записываю")
            return "в config.json ошибка. Исправь её или удали файл, он создастся заново."
        change(data)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return None

    def save_setting(self, key: str, value: Any) -> None:
        self._edit(lambda data: data.__setitem__(key, value))

    def save_entry(self, section: str, name: str, value: Any) -> str | None:
        """Встроенные записи убираются пометкой null, иначе вернулись бы из настроек по умолчанию."""
        def change(data: dict[str, Any]) -> None:
            entries = data.setdefault(section, {})
            if value is None and name not in DEFAULTS.get(section, {}):
                entries.pop(name, None)
            else:
                entries[name] = value
        return self._edit(change)

    def modified_time(self) -> float | None:
        try:
            return os.path.getmtime(self._path)
        except OSError:
            return None

    def load(self) -> SettingsLoadResultDTO:
        cfg = json.loads(json.dumps(DEFAULTS))
        if self._blank():  # файла нет или его содержимое стёрли — создаём заново со стандартными настройками
            log.info("config.json пустой или удалён, создаю заново")
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
            return SettingsLoadResultDTO(settings=cfg)
        try:
            with open(self._path, encoding="utf-8-sig") as f:
                user = json.load(f)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    for name, value in v.items():  # null — убранная встроенная запись
                        if value is None:
                            cfg[k].pop(name, None)
                        else:
                            cfg[k][name] = value
                else:
                    cfg[k] = v
            missing = [k for k in DEFAULTS if k not in user]
            if missing:  # файл неполный (его создал setup_ai.bat или он из старой версии) — дописываем
                self._edit(lambda data: [data.setdefault(k, DEFAULTS[k]) for k in missing])
                log.info("В config.json добавлены недостающие настройки: %s", ", ".join(missing))
        except json.JSONDecodeError as e:
            log.error("config.json с ошибкой (строка %d, символ %d: %s), использую настройки по умолчанию",
                      e.lineno, e.colno, e.msg)
            return SettingsLoadResultDTO(
                settings=json.loads(json.dumps(DEFAULTS)),
                error=(f"В config.json ошибка в строке {e.lineno}, я его не прочитала и работаю "
                       "со стандартными настройками. Проверь там кавычки, запятые и двойные слеши в путях."))
        except Exception:
            log.exception("config.json не прочитался, использую настройки по умолчанию")
            return SettingsLoadResultDTO(settings=json.loads(json.dumps(DEFAULTS)),
                                         error="Не смогла прочитать config.json, работаю со стандартными настройками.")
        return SettingsLoadResultDTO(settings=cfg)
