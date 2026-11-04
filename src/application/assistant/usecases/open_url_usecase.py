from src.application.assistant.command_context import CommandContext
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter
from src.application.assistant.interfaces.i_open_url_usecase import IOpenUrlUseCase


class OpenUrlUseCase(IOpenUrlUseCase):
    """Открыть адрес: в браузере из команды («… в хроме»), из настройки "browser" или в браузере
    по умолчанию Windows."""

    def __init__(self, context: CommandContext, browser: IBrowserAdapter) -> None:
        self._context = context
        self._browser = browser

    def __call__(self, url: str) -> None:
        exe = (self._browser.find_browser(self._context.browser_once)
               or self._browser.find_browser(self._context.settings.get("browser")))
        self._browser.open_url(url, exe)
