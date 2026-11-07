from src.application.assistant.command_context import CommandContext
from src.application.assistant.interfaces.i_remember_entry_usecase import IRememberEntryUseCase
from src.application.assistant.interfaces.i_settings_store import ISettingsStore
from src.application.assistant.text import Text


class RememberEntryUseCase(IRememberEntryUseCase):
    """Записать сайт / программу / свой ответ в config.json и сразу начать их узнавать."""

    def __init__(self, context: CommandContext, store: ISettingsStore) -> None:
        self._context = context
        self._store = store

    def __call__(self, section: str, name: str, target: str | None) -> str | None:
        name = Text.norm(name)
        err = self._store.save_entry(section, name, target)
        if err:
            return err
        book = self._context.book(section)
        stored = self._context.settings.setdefault(section, {})
        if target is None:
            book.pop(name, None)
            stored.pop(name, None)
        else:
            book[name] = target
            stored[name] = target
        return None
