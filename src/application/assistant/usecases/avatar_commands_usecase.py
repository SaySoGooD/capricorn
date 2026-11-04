import datetime
import re

from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_avatar_commands_usecase import IAvatarCommandsUseCase
from src.application.assistant.persona import line

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
DAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


class AvatarCommandsUseCase(IAvatarCommandsUseCase):
    """Команды самой Капри: уйти, помахать, погулять, переместиться, сказать время."""

    def quit(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("quit"), "quit")

    def hide(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("hide"), "hide")

    def wave(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("wave"), "wave")

    def roam(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("roam"), "roam")

    def help(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("help"))

    def move(self, c: str, m: re.Match) -> ReplyDTO:
        """Куда переместиться: «в левый нижний угол», «вправо», «в центр», «в другую сторону»."""
        if re.search(r"другую сторону|в другую", c):
            where = "other"
        elif re.search(r"центр|середин", c):
            where = "center"
        else:
            h = "left" if re.search(r"лев|влево", c) else "right" if re.search(r"прав|вправо", c) else ""
            v = "top" if re.search(r"верх|наверх", c) else "bottom" if re.search(r"низ|вниз", c) else ""
            where = "-".join(x for x in (v, h) if x) or "other"
        return ReplyDTO(line("move"), "move:" + where)

    def time(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("time", t=f"{datetime.datetime.now():%H:%M}"))

    def date(self, c: str, m: re.Match) -> ReplyDTO:
        d = datetime.date.today()
        return ReplyDTO(line("date", t=f"{DAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"))
