import re
import threading
import time

from src.application.assistant.command_chain import CommandChain
from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter
from src.application.assistant.interfaces.i_input_commands_usecase import IInputCommandsUseCase
from src.application.assistant.interfaces.i_keyboard_adapter import IKeyboardAdapter
from src.application.assistant.interfaces.i_ui_automation_adapter import IUiAutomationAdapter
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.keys import Keys
from src.application.assistant.media_time import MediaTime
from src.application.assistant.persona import persona
from src.application.assistant.text import Text


class InputCommandsUseCase(IInputCommandsUseCase):
    """Клавиатура, прокрутка, окна и вкладки, печать текста."""

    def __init__(
        self,
        context: CommandContext,
        keyboard: IKeyboardAdapter,
        window: IWindowAdapter,
        youtube: IYouTubePlayerAdapter,
        browser: IBrowserAdapter,
        ui_automation: IUiAutomationAdapter,
    ) -> None:
        self._context = context
        self._keyboard = keyboard
        self._window = window
        self._youtube = youtube
        self._browser = browser
        self._ui = ui_automation

    # --- прокрутка ---
    def scroll(self, c: str, m: re.Match) -> ReplyDTO | None:
        up = bool(re.search(r"\b(вверх|наверх|выше|верх\w*|начал\w*|поднимись|назад)\b", c))
        down = bool(re.search(r"\b(вниз|ниже|низ\w*|конец|дальше|спустись|вперед)\b", c))
        auto = re.search(r"\b(медленно|плавно|автоматически|сама|постепенно|прокручивай|листай сама)\b", c) \
            or re.fullmatch(r"(листай|полистай|прокручивай|скроль|скролль)( медленно| плавно)?", c)
        if not (up or down or auto) or re.search(r"секунд|минут|\bчас|\d[:.]\d\d|полминут", c):
            return None  # «прокрути на 30 секунд вперёд» — это перемотка видео, не страницы
        direction = -1 if up and not down else 1
        self.stop_background()
        if auto:
            fast = bool(re.search(r"быстр", c))
            stop = self._context.autoscroll_stop = threading.Event()
            threading.Thread(target=self._autoscroll, args=(direction, 0.25 if fast else 0.6, stop),
                             daemon=True).start()
            return ReplyDTO(persona.line("scroll_auto"))
        if re.search(r"\b(самый|самую|самого|до конца|в конец|в начало|до низа|до верха|конец страницы|"
                     r"начало страницы)\b|^(в |на |до )?(низ|верх|низа|верха)$", c):
            self._window.scroll(200 * direction, delay=0.008)  # слишком быстро — щелчки колеса теряются
            return ReplyDTO(persona.line("scroll_end" if direction > 0 else "scroll_top"))
        n = Text.parse_number(c)
        screen = self._window.screen_notches()
        if re.search(r"\b(немного|чуть|чуть-чуть|слегка|капельку)\b|^(еще )?(ниже|выше)$", c):
            notches = 3
        elif n and re.search(r"экран|страниц|раз", c):
            notches = min(n, 20) * screen
        else:
            notches = screen
        self._window.scroll(notches * direction)
        return ReplyDTO(persona.line("scroll"))

    def _autoscroll(self, direction: int, interval: float, stop: threading.Event) -> None:
        """Плавная прокрутка в окне, которое было активно в момент команды, — пока не скажут «стоп»."""
        hwnd = self._window.target_window()
        end = time.time() + 300
        while not stop.is_set() and time.time() < end:
            if self._window.target_window() != hwnd:
                break  # пользователь ушёл в другое окно — не крутим чужое
            self._window.scroll(direction, hwnd=hwnd)
            stop.wait(interval)

    def autoscroll_active(self) -> bool:
        ev = self._context.autoscroll_stop
        return bool(ev and not ev.is_set())

    def stop_background(self) -> bool:
        """Остановить фоновые действия (автопрокрутку). True — было что останавливать."""
        ev = self._context.autoscroll_stop
        if ev and not ev.is_set():
            ev.set()
            return True
        return False

    # --- клавиши, вкладки, окна ---
    def press(self, c: str, m: re.Match) -> ReplyDTO | None:
        text = m.group("k")
        times = 1
        rep = re.search(r"\s(\S+) раз\w*$", text)
        if rep and Text.parse_number(rep.group(1)):
            times, text = min(30, Text.parse_number(rep.group(1))), text[:rep.start()]
        keys, unknown = Keys.parse_keys(text)
        if unknown:
            return ReplyDTO(persona.line("key_unknown", t=unknown))
        if not keys:
            return None
        for _ in range(times):
            self._keyboard.send_keys(keys)
            time.sleep(0.08)
        return ReplyDTO(persona.line("pressed", t=" + ".join(k.upper() if len(k) == 1 else k.capitalize() for k in keys)))

    def tab(self, c: str, m: re.Match) -> ReplyDTO:
        send = self._keyboard.send_keys
        if re.search(r"нов(ую|ая) вкладк", c):
            send(["ctrl", "t"])
            return ReplyDTO(persona.line("tab_new"))
        if re.search(r"\b(верни|восстанови)", c):
            send(["ctrl", "shift", "t"])
            return ReplyDTO(persona.line("tab_restore"))
        if re.search(r"следующ", c):
            send(["ctrl", "tab"])
            return ReplyDTO(persona.line("done"))
        if re.search(r"предыдущ", c):
            send(["ctrl", "shift", "tab"])
            return ReplyDTO(persona.line("done"))
        n = max(1, min(20, Text.parse_number(c) or 1))
        for _ in range(n):
            send(["ctrl", "w"])
            time.sleep(0.12)
        return ReplyDTO(persona.line("tab_closed", n=n) if n > 1 else persona.line("tab_closed_one"))

    def switch_tab(self, c: str, m: re.Match) -> ReplyDTO | None:
        """«перейди на вторую вкладку», «открой первую вкладку», «последнюю вкладку» → Ctrl+1..8/9."""
        if re.search(r"\bпоследн", c):
            n = 9  # Ctrl+9 в браузерах — последняя вкладка
        else:
            # порядковые в любом роде («вторую», «седьмую») → количественное → число
            n = Text.parse_number(MediaTime.ordinals_to_cardinals(c))
        if not n:
            return None
        self._browser.switch_tab(n)
        return ReplyDTO(persona.line("done"))

    def click(self, c: str, m: re.Match) -> ReplyDTO:
        """«нажми на кнопку войти», «кликни по сохранить» — клик по элементу окна через UI Automation."""
        name = (m.group("name") or "").strip(" .,!?:;«»\"'")
        if not name:
            return ReplyDTO(persona.line("click_not_found", t=""))
        ok = self._ui.click_element(name)
        return ReplyDTO(persona.line("clicked", t=name) if ok else persona.line("click_not_found", t=name))

    def minimize_all(self, c: str, m: re.Match) -> ReplyDTO:
        self._keyboard.send_keys(["win", "d"])
        return ReplyDTO(persona.line("done"))

    def minimize(self, c: str, m: re.Match) -> ReplyDTO:
        """«Сверни окно / вкладку / браузер» — сворачивает активное окно."""
        self._window.minimize_foreground()
        return ReplyDTO(persona.line("done"))

    def search_field(self, c: str, m: re.Match) -> ReplyDTO:
        self._window.focus_search(self._window.foreground_title())
        return ReplyDTO(persona.line("search_ready"))

    # --- печать ---
    def type_cmd(self, c: str, m: re.Match) -> ReplyDTO | None:
        """«напиши привет» — печатает в активное окно и жмёт Enter (в чате это отправка)."""
        parsed = CommandChain.parse_type(c)
        if not parsed:
            return None  # «напиши стих» — это просьба к нейросети, а не печать
        text, send = parsed
        title = self._window.foreground_title().lower()
        recent_yt = time.time() - self._context.youtube_opened_at < 120
        if "youtube" in title or (recent_yt and self._youtube.window_present()):
            # на YouTube «напиши X» = поиск X (печатать в саму страницу бессмысленно)
            if "youtube" not in title and not self._window.wait_and_focus(("youtube",), timeout=4):
                return ReplyDTO(persona.line("focus_fail"))
            self._youtube.search_in_tab(text)
            return ReplyDTO(persona.line("yt", q=text))
        if send is None:
            send = self._context.settings.get("type_press_enter", True)
        self._keyboard.input_text(text)
        if send:
            time.sleep(0.1)
            self._keyboard.send_keys(["enter"])
        return ReplyDTO(persona.line("sent" if send else "typed", t=text))
