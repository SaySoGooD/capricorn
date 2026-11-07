"""Капри сама водит свой браузер (CDP): открывает сайты, читает страницы, ходит по ссылкам.

Браузер — настоящий Chrome с отдельным чистым профилем, без флагов автоматизации (см. адаптер), поэтому
антибот видит обычного пользователя. Запуск браузера может занять пару секунд — делаем в рабочем потоке."""
import logging
import re

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_browser_automation_adapter import IBrowserAutomationAdapter
from src.application.assistant.interfaces.i_browser_automation_usecase import IBrowserAutomationUseCase
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.persona import persona

log = logging.getLogger("capri")

SUMMARY_SYSTEM = (
    persona.CHARACTER + "\n\n" + persona.SPEECH_RULES +
    "\n\nНиже — текст веб-страницы, которую ты открыла в своём браузере. Перескажи кратко своими словами, "
    "о чём она и что главное, 2–3 предложения. Опирайся ТОЛЬКО на этот текст, ничего не додумывай."
)


class BrowserAutomationUseCase(IBrowserAutomationUseCase):
    def __init__(
        self,
        context: CommandContext,
        browser: IBrowserAutomationAdapter,
        local_chat: ILocalChatModelAdapter | None = None,
    ) -> None:
        self._context = context
        self._browser = browser
        self._local = local_chat

    def _enabled(self) -> bool:
        return bool(self._context.settings.get("browser_cdp", True))

    def open_browser(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._enabled():
            return ReplyDTO(persona.line("browser_off"))
        if self._browser.available:
            return ReplyDTO(persona.line("browser_already"))
        ok = self._browser.launch()
        return ReplyDTO(persona.line("browser_launched" if ok else "browser_fail"))

    def open_site(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._enabled():
            return ReplyDTO(persona.line("browser_off"))
        url = m.group("q").strip(" .,!?:;«»\"'")
        if not url:
            return ReplyDTO(persona.line("browser_fail"))
        if self._browser.open(url):
            return ReplyDTO(persona.line("browser_opened", q=url))
        return ReplyDTO(persona.line("browser_fail"))

    def read_page(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._enabled():
            return ReplyDTO(persona.line("browser_off"))
        if not self._browser.available:
            return ReplyDTO(persona.line("browser_not_open"))
        text = self._browser.page_text()
        if not text:
            return ReplyDTO(persona.line("browser_read_empty"))
        if self._local and self._local.available:  # пересказываем своими словами по тексту страницы
            summary = self._local.instruct(SUMMARY_SYSTEM + "\n\nТЕКСТ СТРАНИЦЫ:\n" + text[:6000], "Перескажи кратко.")
            if summary:
                return ReplyDTO(summary, "answer")
        return ReplyDTO(persona.line("browser_read", q=text[:280]), "answer")

    def list_links(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._enabled():
            return ReplyDTO(persona.line("browser_off"))
        if not self._browser.available:
            return ReplyDTO(persona.line("browser_not_open"))
        links = self._browser.links()
        names = [t for t, _ in links if len(t) > 1][:7]
        if not names:
            return ReplyDTO(persona.line("browser_no_links"))
        return ReplyDTO(persona.line("browser_links", q="; ".join(names)), "answer")

    def click_link(self, c: str, m: re.Match) -> ReplyDTO | None:
        if not self._enabled():
            return ReplyDTO(persona.line("browser_off"))
        if not self._browser.available:
            return ReplyDTO(persona.line("browser_not_open"))
        target = m.group("q").strip(" .,!?:;«»\"'")
        href = self._browser.click_link(target)
        if not href:
            return ReplyDTO(persona.line("browser_link_missing", q=target))
        return ReplyDTO(persona.line("browser_link_clicked", q=target))

    def close_browser(self, c: str, m: re.Match) -> ReplyDTO | None:
        running = self._browser.available
        self._browser.close()
        return ReplyDTO(persona.line("browser_closed" if running else "browser_not_open"))
