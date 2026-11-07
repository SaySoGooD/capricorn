import re

from src.application.assistant.command_chain import CommandChain
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_app_catalog_adapter import IAppCatalogAdapter
from src.application.assistant.interfaces.i_messenger_adapter import IMessengerAdapter
from src.application.assistant.interfaces.i_messenger_commands_usecase import IMessengerCommandsUseCase
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.persona import persona
from src.application.assistant.text import Text


class MessengerCommandsUseCase(IMessengerCommandsUseCase):
    """Чаты Telegram: «первый чат», «чат мама», «открой телеграм папа»."""

    def __init__(
        self,
        window: IWindowAdapter,
        catalog: IAppCatalogAdapter,
        messenger: IMessengerAdapter,
    ) -> None:
        self._window = window
        self._catalog = catalog
        self._messenger = messenger

    def chat(self, c: str, m: re.Match) -> ReplyDTO:
        """Открывает чат в Telegram (запускает его, если надо)."""
        if not self._window.find_window(("telegram",)):
            found = self._catalog.candidates("телеграм", {"телеграм": "telegram"}, 1) \
                if self._catalog.wait_ready(8) else []
            if not found:
                return ReplyDTO(persona.line("app_missing", t="Telegram"), "fail")
            self._catalog.launch(found[0].target)
        index = CommandChain.ORDINALS.get(m.groupdict().get("ord") or "", None)
        name = (m.groupdict().get("name") or "").strip() or None
        if name:
            name = re.sub(r"^(с|со|контакт\w*|чат\w*|chat|с контактом)\s+", "", name)
            name = Text.stem_name(name)
        if not self._messenger.open_chat(index=index or (None if name else 1), name=name):
            # чат не открылся — дальше по цепочке ничего не печатаем, чтобы не написать не туда
            return ReplyDTO(persona.line("chat_not_found", t=name or f"номер {index or 1}"), "fail")
        return ReplyDTO(persona.line("chat_open", t=name or f"чат номер {index or 1}"))
