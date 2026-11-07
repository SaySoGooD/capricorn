import random
import re
import urllib.parse

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_encyclopedia_adapter import IEncyclopediaAdapter
from src.application.assistant.interfaces.i_open_url_usecase import IOpenUrlUseCase
from src.application.assistant.interfaces.i_web_commands_usecase import IWebCommandsUseCase
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.interfaces.i_youtube_search_adapter import IYouTubeSearchAdapter
from src.application.assistant.persona import persona
from src.application.assistant.text import Text

GOOGLE = "https://www.google.com/search?q="
YOUTUBE_SEARCH = "https://www.youtube.com/results?search_query="


class WebCommandsUseCase(IWebCommandsUseCase):
    """Поиск в интернете, картинки, справка, видео на YouTube."""

    def __init__(
        self,
        context: CommandContext,
        open_url: IOpenUrlUseCase,
        youtube_search: IYouTubeSearchAdapter,
        youtube: IYouTubePlayerAdapter,
        encyclopedia: IEncyclopediaAdapter,
    ) -> None:
        self._context = context
        self._open_url = open_url
        self._youtube_search = youtube_search
        self._youtube = youtube
        self._encyclopedia = encyclopedia

    def search(self, c: str, m: re.Match) -> ReplyDTO:
        q = m.group("q")
        yt = re.search(r"(на|в) (ютубе|ютуб|youtube)", q)
        if yt:
            q = q.replace(yt.group(0), "").strip()
            self._open_url(YOUTUBE_SEARCH + urllib.parse.quote(q))
            return ReplyDTO(persona.line("yt", q=q))
        self._open_url(GOOGLE + urllib.parse.quote(q))
        return ReplyDTO(persona.line("web", q=q))

    def images(self, c: str, m: re.Match) -> ReplyDTO:
        q = m.group("q").strip()
        if re.search(r"\bобои\b", c):
            q = "обои " + q
        self._open_url("https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(q))
        return ReplyDTO(persona.line("images", q=q))

    def info(self, c: str, m: re.Match) -> ReplyDTO:
        """Открывает поиск Google и вслух пересказывает начало статьи из Википедии, если она нашлась."""
        q = m.group("q").strip()
        self._open_url(GOOGLE + urllib.parse.quote(q))
        summary = self._encyclopedia.summary(q)
        if summary:
            return ReplyDTO(persona.line("info", t=summary))
        return ReplyDTO(persona.line("web", q=q))

    def video(self, c: str, m: re.Match) -> ReplyDTO:
        q = m.group("q").strip()
        q = re.sub(r"\s+(на|в) (ютуб\w*|youtube)$", "", q)  # «включи песню X на ютубе»
        q = re.sub(r"^(на|в) (ютуб\w*|youtube)\s*", "", q).strip()
        if not q or q in ("на", "в", "с", "про", "о"):  # «открой какое-нибудь видео на ютубе»
            q = random.choice(["интересное видео", "смешные моменты", "залипательное видео", "лучшие клипы"])
        kind = m.groupdict().get("kind") or ""
        search = q + (" песня" if re.match(r"песн|трек", kind) else "")
        found = self._youtube_search.first_video(search)
        if not found:  # не вышло достать первое видео — хотя бы откроем поиск
            self._open_url(YOUTUBE_SEARCH + urllib.parse.quote(search))
            return ReplyDTO(persona.line("yt", q=q))
        self._open_url(f"https://www.youtube.com/watch?v={found.video_id}")
        self._youtube.ensure_playing_async()
        title = re.sub(r"\s+", " ", found.title).strip()
        if len(title) > 70:
            title = title[:67].rsplit(" ", 1)[0] + "…"
        return ReplyDTO(persona.line("video", t=title) if title else persona.line("video_untitled"))

    def fallback(self, cmd: str, force_search: bool = False) -> ReplyDTO:
        """Без ответа нейросети: вопрос ищем в Google (если search_when_unsure не выключен),
        остальное — «не знаю такой команды»."""
        c = Text.norm(cmd)
        if force_search or re.match(r"^(что|кто|как|какой|какая|какое|какие|почему|зачем|сколько|где|когда|куда|"
                                    r"откуда|чем|чей|расскажи|объясни|скажи)\b", c):
            if not self._context.settings.get("search_when_unsure", True):
                return ReplyDTO(persona.line("dont_know"))
            self._open_url(GOOGLE + urllib.parse.quote(cmd))
            return ReplyDTO(persona.line("search_q"))
        return ReplyDTO(persona.line("unknown"))
