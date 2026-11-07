import difflib
import os
import re

from src.application.assistant.command_context import CommandContext
from src.application.assistant.commands import CAPRI_URL
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter
from src.application.assistant.interfaces.i_memory_commands_usecase import IMemoryCommandsUseCase
from src.application.assistant.interfaces.i_open_url_usecase import IOpenUrlUseCase
from src.application.assistant.interfaces.i_remember_entry_usecase import IRememberEntryUseCase
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.persona import persona
from src.application.assistant.processes import PROTECTED_PROCS
from src.application.assistant.text import Text


class MemoryCommandsUseCase(IMemoryCommandsUseCase):
    """Свои сайты, программы и ответы: «запомни этот сайт как музыка», «когда я скажу X, отвечай Y»."""

    def __init__(
        self,
        context: CommandContext,
        remember: IRememberEntryUseCase,
        browser: IBrowserAdapter,
        window: IWindowAdapter,
        open_url: IOpenUrlUseCase,
    ) -> None:
        self._context = context
        self._remember = remember
        self._browser = browser
        self._window = window
        self._open_url = open_url

    def custom_reply(self, c: str) -> ReplyDTO | None:
        """Свой ответ на фразу из config.json → "replies" (точно или почти дословно) или None."""
        replies = self._context.replies
        if not replies:
            return None
        if c in replies:
            return ReplyDTO(replies[c])
        close = difflib.get_close_matches(c, list(replies), n=1, cutoff=0.85)
        if close:
            return ReplyDTO(replies[close[0]])
        # фраза целиком внутри команды и лишнего немного: «ну как дела» → «как дела»
        for phrase in sorted(replies, key=len, reverse=True):
            if len(c) - len(phrase) <= 12 and re.search(rf"(^|\s){re.escape(phrase)}(\s|$)", c):
                return ReplyDTO(replies[phrase])
        return None

    def remember_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        """«запомни этот сайт как музыка» — адрес открытой вкладки; «запомни эту программу как запрет» —
        программа, окно которой сейчас на экране."""
        name = re.sub(r"^(как|под названием|под именем|с названием|назови)\s+", "", (m.group("name") or "").strip())
        name = name.strip(" «»\"")
        site = re.search(r"(сайт|страниц|вкладк|ссылк)", m.group("what"))
        if not name:
            return ReplyDTO(persona.line("remember_noname", what="этот сайт" if site else "эту программу"))
        if site:
            url = self._browser.foreground_page_url()
            if not url:
                return ReplyDTO(persona.line("remember_nosite"))
            err = self._remember("sites", name, url)
            short = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            return ReplyDTO(persona.line("remember_fail", e=err) if err else persona.line("remember_site", t=name, url=short))
        exe = self._window.foreground_exe()
        base = os.path.splitext(os.path.basename(exe or ""))[0].lower()
        if not exe or base in PROTECTED_PROCS or base == "applicationframehost":
            return ReplyDTO(persona.line("remember_noapp"))
        err = self._remember("apps", name, exe)
        return ReplyDTO(persona.line("remember_fail", e=err) if err else persona.line("remember_app", t=name, app=base))

    def forget_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        name = Text.norm(m.group("name"))
        section = "sites" if re.search(r"(сайт|страниц|вкладк|ссылк)", m.group("what")) else "apps"
        if name not in self._context.book(section):
            return ReplyDTO(persona.line("forget_missing", t=name))
        err = self._remember(section, name, None)
        return ReplyDTO(persona.line("remember_fail", e=err) if err else persona.line("forget_ok", t=name))

    def updates(self, c: str, m: re.Match) -> ReplyDTO:
        """Страница Капри на GitHub — там новые версии."""
        self._open_url(CAPRI_URL)
        return ReplyDTO(persona.line("updates"))

    def reply_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        """«Когда я скажу „как дела“, отвечай „лучше всех“» — свой ответ на фразу."""
        phrase = m.group("p").strip(" ,")
        text = m.group("r").strip(" ,")
        text = text[:1].upper() + text[1:]
        if not re.search(r"[.!?…]$", text):
            text += "."
        err = self._remember("replies", phrase, text)
        return ReplyDTO(persona.line("remember_fail", e=err) if err else persona.line("reply_saved", p=phrase, r=text))

    def forget_reply_cmd(self, c: str, m: re.Match) -> ReplyDTO:
        phrase = Text.norm(m.group("p"))
        replies = self._context.replies
        close = phrase if phrase in replies else next(
            iter(difflib.get_close_matches(phrase, list(replies), n=1, cutoff=0.85)), None)
        if not close:
            return ReplyDTO(persona.line("forget_missing", t=phrase))
        err = self._remember("replies", close, None)
        return ReplyDTO(persona.line("remember_fail", e=err) if err else persona.line("forget_ok", t=close))
