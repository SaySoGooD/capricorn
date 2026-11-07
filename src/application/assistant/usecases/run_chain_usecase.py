import logging
import re
import time
from collections.abc import Callable

from src.application.assistant.command_chain import CommandChain
from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_keyboard_adapter import IKeyboardAdapter
from src.application.assistant.interfaces.i_messenger_adapter import IMessengerAdapter
from src.application.assistant.interfaces.i_run_chain_usecase import IRunChainUseCase
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.persona import persona
from src.application.assistant.text import Text

log = logging.getLogger("capri")

KIND_OF_WORD = {"telegram": "telegram", "телеграм": "telegram", "телега": "telegram",
                "ютуб": "youtube", "youtube": "youtube"}


class RunChainUseCase(IRunChainUseCase):
    """«открой телеграм, первый чат, напиши привет» — шаги по очереди, с памятью о текущем окне."""

    def __init__(
        self,
        context: CommandContext,
        keyboard: IKeyboardAdapter,
        window: IWindowAdapter,
        youtube: IYouTubePlayerAdapter,
        messenger: IMessengerAdapter,
    ) -> None:
        self._context = context
        self._keyboard = keyboard
        self._window = window
        self._youtube = youtube
        self._messenger = messenger

    def _enter(self) -> None:
        time.sleep(0.1)
        self._keyboard.send_keys(["enter"])

    def __call__(self, steps: list[str], handle_one: Callable[[str], ReplyDTO | None]) -> ReplyDTO:
        log.info("Цепочка: %s", steps)
        context = None   # ключевые слова заголовка окна, с которым работаем
        kind = None      # telegram / youtube / browser / None
        said: list[str] = []
        in_search = False  # курсор уже стоит в поле поиска
        field_focused = False  # после клика по элементу курсор уже в нужном поле — печатаем туда, а не в поиск

        def fail() -> ReplyDTO:
            return ReplyDTO(" ".join(said + [persona.line("focus_fail")]))

        for step in steps:
            s = Text.norm(step)
            typed = CommandChain.parse_type(s)
            if typed:
                text, send = typed
                if context and not self._window.wait_and_focus(context, timeout=6):
                    # не смогли переключиться — ничего не печатаем, чтобы не написать в чужое окно
                    return fail()
                if kind == "youtube":
                    self._youtube.search_in_tab(text)
                    said.append(persona.line("yt", q=text))
                    continue
                if kind == "browser" and not field_focused:
                    # на сайте «напиши X» = поиск X: сначала курсор в строку поиска, потом Enter
                    if not in_search:
                        self._window.focus_search(self._window.foreground_title())
                        time.sleep(0.4)
                    self._keyboard.input_text(text)
                    if send is not False:
                        self._enter()
                    said.append(persona.line("web", q=text))
                    continue
                if send is None:
                    send = self._context.settings.get("type_press_enter", True)
                self._keyboard.input_text(text)
                if send:
                    self._enter()
                said.append(persona.line("sent" if send else "typed", t=text))
                continue
            q = re.match(r"^(найди|поищи)\s+(?P<q>.+)$", s)
            if q and kind in ("youtube", "telegram"):
                if kind == "telegram":  # поиск в Telegram = открыть чат по имени
                    if not self._messenger.open_chat(name=q.group("q")):
                        return fail()
                else:
                    if not context or not self._window.wait_and_focus(context, timeout=6):
                        return fail()
                    self._youtube.search_in_tab(q.group("q"))
                    said.append(persona.line("yt", q=q.group("q")))
                continue
            if re.match(r"^(нажми на поиск|нажми поиск|поиск|в поиск|перейди в поиск)$", s):
                if context and not self._window.wait_and_focus(context, timeout=6):
                    return fail()
                self._window.focus_search(self._window.foreground_title())
                time.sleep(0.3)
                in_search = True
                continue
            r = handle_one(s)
            if r is None:
                said.append(persona.line("chain_skip", t=step))
                continue
            if r.action in ("fail", "ask"):  # шаг не удался или нужно уточнить — дальше не идём
                return ReplyDTO(" ".join(said + [r.text]))
            if re.match(r"^(кликни|клик|клацни|ткни|нажми( на| по)? "
                        r"(кнопк|кнопке|ссылк|ссылке|пункт|элемент|поле|галочк|чекбокс|переключател))", s):
                field_focused = True  # кликнули по элементу — следующий «напиши X» уйдёт в него, не в поиск
            for w in s.split():
                if w in CommandChain.APP_WINDOWS:
                    context = CommandChain.APP_WINDOWS[w]
                    kind = KIND_OF_WORD.get(w, "browser" if w == "браузер" else None)
            if re.search(r"\b(чат|диалог|переписк)", s):
                context, kind = ("telegram",), "telegram"
            if context and re.match(r"^(открой|запусти|зайди|перейди)\b", s):
                self._window.wait_and_focus(context, timeout=10)
                time.sleep(2.5 if kind in ("youtube", "browser") else 0.4)  # сайту нужно загрузиться
                in_search = False
        return ReplyDTO(" ".join(said) if said else persona.line("done"))
