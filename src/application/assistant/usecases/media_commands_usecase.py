import re
import time

from src.application.assistant.browsers import BROWSERS
from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_media_commands_usecase import IMediaCommandsUseCase
from src.application.assistant.interfaces.i_media_session_adapter import IMediaSessionAdapter
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.media_time import fmt, number_groups, parse_time
from src.application.assistant.persona import line


class MediaCommandsUseCase(IMediaCommandsUseCase):
    """То, что сейчас играет: музыка, YouTube в браузере, плееры."""

    def __init__(
        self,
        context: CommandContext,
        media: IMediaSessionAdapter,
        youtube: IYouTubePlayerAdapter,
    ) -> None:
        self._context = context
        self._media = media
        self._youtube = youtube

    def media_pause(self, c: str, m: re.Match) -> ReplyDTO:
        yt = self._youtube
        if yt.browser_playing() and yt.window_present():
            # YouTube в браузере: системная пауза не всегда доходит — проверяем по звуку и жмём K
            self._media.control("pause")
            time.sleep(0.8)
            if yt.browser_playing():
                yt.press_player_keys([["k"]])
                time.sleep(0.8)
            if not yt.browser_playing():
                self._context.media_paused = "youtube"
                return ReplyDTO(line("media_paused"))
        result = self._media.control("pause")
        if not result.ok:
            return ReplyDTO(line("media_none"))
        self._context.media_paused = result.source  # «продолжи» вернёт именно это, а не другой плеер
        return ReplyDTO(line("media_paused"))

    def media_play(self, c: str, m: re.Match) -> ReplyDTO:
        yt = self._youtube
        paused = self._context.media_paused
        if paused == "youtube" or (not paused and yt.window_present() and not self._media.now_playing()):
            def started() -> bool:
                for _ in range(8):  # у трансляций звук появляется не сразу
                    time.sleep(0.5)
                    if yt.browser_playing():
                        return True
                return False
            for b in BROWSERS:  # сначала системной командой — без переключения окон
                if self._media.control("play", source=f"{b}.exe").ok:
                    break
            if started() or (yt.press_player_keys([["k"]]) and started()):
                return ReplyDTO(line("media_play"))
            if paused == "youtube":  # не включаем вместо YouTube какой-то другой плеер
                return ReplyDTO(line("media_play_fail"))
        if not self._media.control("play", source=paused).ok:
            return ReplyDTO(line("media_none"))
        return ReplyDTO(line("media_play"))

    def media_next(self, c: str, m: re.Match) -> ReplyDTO:
        if not self._media.control("next").ok:
            return ReplyDTO(line("media_none"))
        time.sleep(0.8)  # даём плееру переключиться, чтобы назвать новый трек
        info = self._media.now_playing()
        return ReplyDTO(line("media_next", t=info.title) if info and info.title else line("done"))

    def media_prev(self, c: str, m: re.Match) -> ReplyDTO:
        return ReplyDTO(line("done") if self._media.control("prev").ok else line("media_none"))

    def media_info(self, c: str, m: re.Match) -> ReplyDTO:
        info = self._media.now_playing()
        if not info or not info.title:
            return ReplyDTO(line("media_none"))
        return ReplyDTO(line("media_info", t=info.title))

    def media_seek(self, c: str, m: re.Match) -> ReplyDTO | None:
        back = re.search(r"\bназад\b|\bотмотай|\bверни|\bвернись", c)
        fwd = re.search(r"\bвперед|\bпромотай|\bпропусти|\bскипни|\bмотни", c)
        text = re.sub(r"^(поставь|включи|начни|запусти|давай|играй|воспроизведи|перемотай|перемотать|промотай|"
                      r"мотни|отмотай|прокрути|верни\w*|вернись|пропусти|скипни|перемотка)\s+", "", c)
        text = re.sub(r"\b(вперед|назад|на|с|со|в|к|видео|музык\w*|трек|песн\w*|ролик|момент\w*|отметк\w*|"
                      r"тайминг)\b", " ", text)
        secs = parse_time(text)
        groups = number_groups(text)
        to_start = re.search(r"начал|сначала|заново", c)
        if to_start:
            back = fwd = None  # «верни сначала» — это не «назад», а в самое начало
        absolute = to_start or not (back or fwd) and (
            re.match(r"^(поставь|включи|начни|запусти|давай|играй|воспроизведи)", c)
            or re.search(r"\d[:.]\d\d|момент|отметк|тайминг|позици|\bс (\S+ )?\S+ (минут|секунд|час)", c)
            or len(groups) >= 2
            or (groups and groups[0] >= 100 and not re.search(r"секунд|минут|час", c)))  # «на 314» = 3:14
        if secs is None:
            if not (back or fwd):
                return None
            secs = 10  # «перемотай вперёд» без числа — на 10 секунд
        delta = None if absolute else (-secs if back else secs)
        np = self._media.now_playing()
        yt = self._youtube
        if yt.window_present() and (yt.browser_playing() or not np
                                    or any(b in (np.source or "").lower() for b in BROWSERS)):
            # YouTube в браузере: Firefox не даёт перематывать через систему — клавиши плеера или ссылка с &t=
            if absolute:
                if yt.seek_by_url(secs):
                    yt.ensure_playing_async(5.0)
                    return ReplyDTO(line("media_seek", t=fmt(secs)))
                return ReplyDTO(line("media_seek_fail"))
            n10, rest = divmod(int(abs(delta)), 10)
            keys = [["l" if delta > 0 else "j"]] * n10 + [["right" if delta > 0 else "left"]] * round(rest / 5)
            if yt.press_player_keys(keys or [["right" if delta > 0 else "left"]]):
                return ReplyDTO(line("media_skip", t=fmt(abs(delta)), d="вперёд" if delta > 0 else "назад"))
            return ReplyDTO(line("media_seek_fail"))
        result = self._media.seek(seconds=secs) if absolute else self._media.seek(delta=delta)
        if result.position is None:
            return ReplyDTO(line("media_none"))
        return ReplyDTO(line("media_seek", t=fmt(result.position)) if result.ok else line("media_seek_fail"))
