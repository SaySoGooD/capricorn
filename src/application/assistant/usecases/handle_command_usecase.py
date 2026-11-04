import logging
import re
from collections.abc import Callable

from src.application.assistant.browsers import BROWSER_NAMES, BROWSER_SUFFIX, BROWSER_WORDS
from src.application.assistant.command_chain import ORDINALS, TYPE_VERBS, split_chain
from src.application.assistant.command_context import CommandContext
from src.application.assistant.commands import FORGET_RE, FORGET_REPLY_RE, REMEMBER_RE, REPLY_RE, UPDATES_RE
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_app_commands_usecase import IAppCommandsUseCase
from src.application.assistant.interfaces.i_avatar_commands_usecase import IAvatarCommandsUseCase
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter
from src.application.assistant.interfaces.i_handle_command_usecase import IHandleCommandUseCase
from src.application.assistant.interfaces.i_input_commands_usecase import IInputCommandsUseCase
from src.application.assistant.interfaces.i_media_commands_usecase import IMediaCommandsUseCase
from src.application.assistant.interfaces.i_memory_commands_usecase import IMemoryCommandsUseCase
from src.application.assistant.interfaces.i_messenger_commands_usecase import IMessengerCommandsUseCase
from src.application.assistant.interfaces.i_run_chain_usecase import IRunChainUseCase
from src.application.assistant.interfaces.i_system_commands_usecase import ISystemCommandsUseCase
from src.application.assistant.interfaces.i_web_commands_usecase import IWebCommandsUseCase
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.persona import line
from src.application.assistant.text import norm

log = logging.getLogger("capri")

Handler = Callable[[str, re.Match], ReplyDTO | None]


def build_routes(
    avatar: IAvatarCommandsUseCase,
    memory: IMemoryCommandsUseCase,
    system: ISystemCommandsUseCase,
    input: IInputCommandsUseCase,
    media: IMediaCommandsUseCase,
    messenger: IMessengerCommandsUseCase,
    apps: IAppCommandsUseCase,
    web: IWebCommandsUseCase,
) -> list[tuple[str, Handler]]:
    """Шаблоны команд по порядку: первый подошедший обработчик, вернувший ответ, побеждает."""
    return [
        (r"^(выход|выключись|отключись|заверши работу|завершить работу)$", avatar.quit),
        (r"^(спрячься|скройся|исчезни|пока|отбой|свободна)\b|"
         r"^(уйди|уходи|убирайся|свали|сгинь|испарись|скрой себя|убери себя)\b|"
         r"(уйди|уходи|убирайся|свали|пропади|исчезни) (с|из) (экрана|монитора|глаз)", avatar.hide),
        (REMEMBER_RE, memory.remember_cmd),
        (FORGET_RE, memory.forget_cmd),
        (UPDATES_RE, memory.updates),
        (REPLY_RE, memory.reply_cmd),
        (FORGET_REPLY_RE, memory.forget_reply_cmd),
        (r"помаши|помахай|махни|помаши ручкой|поздоровайся", avatar.wave),
        (r"погуляй|прогуляйся|пройдись|прогулк", avatar.roam),
        (r"что ты (умеешь|можешь)|как\w* (у тебя )?команд|(назови|перечисли|скажи) (\S+ )?команд|"
         r"список команд|помощь$", avatar.help),
        (r"(перемест|подвин|сдвин|переди|встань|иди|отойди|переберись)\w*\s.*(угол|влево|вправо|лев|прав|"
         r"верх|низ|центр|середин|другую сторону)", avatar.move),
        (r"(выключи|перезагрузи|перезапусти) (компьютер|пк|комп|систему)", system.power),
        (r"заблокируй (компьютер|пк|комп|экран)", system.lock),
        (r"громкост|громче|тише|(вкл|выкл|отключ|убер|верни|включ)\w* звук|звук (на|в) |без звука|замуть", system.volume),
        (r"яркост|ярче|темнее", system.brightness),
        (r"(проанализ|анализ|диагност|провер|просканир|сканир)\w*.*(пк|компьютер|комп|систем|ошибк)", system.analyze),
        # --- микрофон (выполняет main: там живёт слушатель) ---
        (r"(какой|какое) (сейчас )?(микрофон|устройство ввода)|что за микрофон|(через )?какой микрофон",
         lambda c, m: ReplyDTO("", "mic_info")),
        (r"(смени|поменяй|переключи|следующий|другой) (\S+ )?(микрофон|устройство ввода)",
         lambda c, m: ReplyDTO("", "mic_next")),
        # --- прокрутка страниц ---
        (r"\b(прокрут|пролист|листай|листани|полистай|скролл|скроль|спустись|поднимись|крути (вниз|вверх))\w*|"
         r"^(в |на |до )?(самый |самую |самого )?(низ|верх|конец страницы|начало страницы|низа|верха)$|"
         r"^(еще |ещё )?(ниже|выше)$", input.scroll),
        # --- мультимедиа: что сейчас играет (музыка, YouTube, плееры) ---
        (r"^(поставь |поставить )?(на )?пауз\w*( музык\w*| видео| трек| песн\w*| ролик)?$|"
         r"^(останови|приостанови|тормозни|стопни)( музык\w*| видео| трек| песн\w*| воспроизведение| ролик)?$|"
         r"^(выключи|стоп) (музык\w*|видео|трек|песн\w*|ролик)$", media.media_pause),
        (r"^(продолжи|продолжай|играй|воспроизведи|сними( с)? пауз\w*|сними)( музык\w*| видео| трек| песн\w*|"
         r" воспроизведение| ролик)?$|^(включи|запусти) (дальше|обратно|снова)$|"
         r"^(включи|запусти) (музык\w*|видео|трек|песн\w*) (обратно|снова|дальше)$", media.media_play),
        (r"^(следующ\w*|дальше|переключи|скипни|пропусти)( трек| песн\w*| видео| композици\w*| ролик)?$|"
         r"^(включи|давай) следующ\w*( трек| песн\w*| видео| ролик)?$", media.media_next),
        (r"^(предыдущ\w*|прошл\w*)( трек| песн\w*| видео| композици\w*| ролик)?$|"
         r"^(включи|верни) (предыдущ|прошл)\w*( трек| песн\w*| видео| ролик)?$", media.media_prev),
        (r"что (сейчас )?(играет|звучит|за (песн|трек|музык|видео)\w*)", media.media_info),
        (r"^(поставь|включи|начни|запусти|давай|играй|воспроизведи)( видео| музык\w*| трек| песн\w*| ролик)? "
         r"(на|с|со) "
         r"(\d|полминут|полтор|начал|сначала|момент|отметк|тайминг|(\S+ ){0,2}(секунд|минут|час)|"
         r"(\S+ )?(ноль|один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|\S+дцать|сорок|"
         r"пятьдесят))", media.media_seek),
        (r"^(перемотай|перемотать|промотай|мотни|отмотай|прокрути|верни\w*|вернись|пропусти|скипни|"
         r"перемотка|поставь|включи)( видео| музык\w*| трек| песн\w*| ролик)?( на| в| к| с)?"
         r"( тайминг\w*| отметк\w*| момент\w*| время| позици\w*)?\s*"
         r"(\d|полминут|полтор|начал|сначала|заново|вперед|назад|(\S+ ){0,2}(секунд|минут|час))", media.media_seek),
        (r"^(включи|начни|поставь|запусти|давай|перемотай|верни|играй)( видео| музык\w*| трек| песн\w*| ролик)?"
         r"( с| на| в)?( самого)? ?(сначала|начало|начала|заново|снова)$", media.media_seek),
        (r"^(нажми на поиск|нажми поиск|перейди в поиск|в поиск|поиск|поставь курсор в поиск)$",
         input.search_field),
        (r"^(нажми|нажать|зажми|жми|набери сочетание) (?P<k>.+)$", input.press),
        (rf"^({TYPE_VERBS})\s+\S", input.type_cmd),
        (r"^(открой |зайди в |перейди в |выбери |найди )?(в )?(телеграм\w*|telegram|телег\w*|тг )?\s*"
         r"((?P<ord>{}) )?(чат\w*|chat|диалог\w*|переписк\w*|контакт\w*|беседу|беседа|группу|канал)"
         r"( с| со)?( (?P<name>.+))?$".format("|".join(ORDINALS)), messenger.chat),
        # «открой телеграм папа» — запустить Telegram и сразу открыть чат с этим именем
        (r"^(открой|зайди в|перейди в|напиши в|запусти) (телеграм\w*|telegram|телег\w*|тг) (?P<name>(?!и |"
         r"напиши|первый|второй|третий).+)$", messenger.chat),
        (r"сверни (все|всё)|покажи рабочий стол", input.minimize_all),
        (r"\bсверни\b", input.minimize),
        (r"(закрой|закрыть|убери) (эту |текущую |\S+ )?вкладк", input.tab),
        (r"нов(ую|ая) вкладк|\b(верни|восстанови) (закрыт\w* )?вкладк|(следующ|предыдущ)\w* вкладк", input.tab),
        (r"^(создай|сделай|создать) (?P<what>.*(папк|файл|документ|таблиц).*)$", apps.create),
        (r"^(найди|покажи|открой|загугли|погугли|поищи)( мне)?( в интернете| в гугле)? (фото\w*|фотк\w*|"
         r"картинк\w*|изображени\w*|пикч\w*|обои)( (с|со|про|о|об|на тему))? (?P<q>.+)$", web.images),
        (r"^(найди|поищи|загугли|погугли|расскажи|узнай|посмотри)( мне)?( в интернете| в гугле| в сети)? "
         r"(информаци\w*|инфу|инфо|что-нибудь|что нибудь|всё|все|сведения|данные|статью)( (о|об|про|по))? "
         r"(?P<q>.+)$", web.info),
        (r"^(открой|включи|покажи|найди|запусти|поставь|врубай|вруби)( мне)?( какое-нибудь| какой-нибудь| "
         r"какое нибудь| любое| любой| одно| одно)? (?P<kind>видео\w*|видос\w*|"
         r"ролик\w*|клип\w*|песн\w*|трек\w*|музык\w*)( на ютуб\w*| в ютуб\w*)?( (с|со|про|о|об|где|на тему))? "
         r"(?P<q>.+)$", web.video),
        (r"^(открой|включи|покажи|запусти|поставь)( мне)? (на|в) (ютуб\w*|youtube) (?P<q>.+)$", web.video),
        (r"^(найди|поищи|загугли|погугли|ищи)( в интернете| в гугле| в google)? (?P<q>.+)$", web.search),
        (r"^(открой|запусти|включи|зайди на|перейди на|покажи) (?P<t>.+)$", apps.open),
        (r"^((сними|снять) (задачу|процесс\w*)|(заверши|завершить|убей|убить|останови|закрой) "
         r"(все )?(процесс\w*|задачу|задачи)|кильни|килльни|грохни|прибей) (?P<t>.+)$", apps.kill_process),
        (r"что (сейчас )?(грузит|нагружает|жрет|ест|тормозит)|(какие|какой) процесс\w* (грузят|нагружают|жрут|"
         r"тормозят)|самые (тяжелые|прожорливые) процессы", system.top_processes),
        (r"^(закрой|заверши|выключи|убей) (?P<t>.+)$", apps.close),
        (r"который час|сколько времени|сколько сейчас времени|время сейчас", avatar.time),
        (r"какое (сегодня )?число|какая (сегодня )?дата|какой сегодня день", avatar.date),
        (r"скриншот|скрин экрана|сделай скрин", system.screenshot),
    ]


class HandleCommandUseCase(IHandleCommandUseCase):
    """Разбор фразы: подтверждения и выбор вариантов, свои ответы, цепочки и отдельные команды."""

    def __init__(
        self,
        context: CommandContext,
        browser: IBrowserAdapter,
        youtube: IYouTubePlayerAdapter,
        run_chain: IRunChainUseCase,
        avatar: IAvatarCommandsUseCase,
        memory: IMemoryCommandsUseCase,
        system: ISystemCommandsUseCase,
        input: IInputCommandsUseCase,
        media: IMediaCommandsUseCase,
        messenger: IMessengerCommandsUseCase,
        apps: IAppCommandsUseCase,
        web: IWebCommandsUseCase,
    ) -> None:
        self._context = context
        self._browser = browser
        self._youtube = youtube
        self._run_chain = run_chain
        self._memory = memory
        self._input = input
        self._apps = apps
        self._web = web
        self._routes = build_routes(avatar, memory, system, input, media, messenger, apps, web)

    def __call__(self, cmd: str) -> ReplyDTO | None:
        c = norm(cmd)
        self._youtube.cancel_ensure()  # новая команда — старая проверка «заиграло ли видео» больше не нужна
        ctx = self._context
        if ctx.pending:
            action, ctx.pending = ctx.pending, None
            if re.match(r"^(да|давай|подтверждаю|конечно|ага)\b", c):
                return action()
            if re.match(r"^(нет|не надо|отмена|стоп)\b", c):
                return ReplyDTO(line("cancel"))
        # любая новая команда останавливает автопрокрутку; «стоп» на этом и заканчивается
        stopped = self._input.stop_background()
        if stopped and re.match(r"^(стоп|хватит|стой|остановись|достаточно|перестань|харэ|все|всё)\b", c):
            return ReplyDTO(line("scroll_stop"))
        if ctx.choice:  # ждём ответ на «какое открыть / закрыть?»
            answer = self._apps.answer_choice(c)
            if answer is not None:
                return answer
            # ответ не про выбор — значит, это новая команда
        custom = self._memory.custom_reply(c)  # своя фраза целиком — не делим её на цепочку команд
        if custom:
            return custom
        # «запомни … как X и Y» — название целиком, не цепочка команд
        whole = any(re.match(p, c) for p in (REMEMBER_RE, FORGET_RE, REPLY_RE, FORGET_REPLY_RE))
        steps = None if whole else split_chain(c)
        if steps:
            try:
                return self._run_chain(steps, self.handle_one)
            except Exception as e:
                log.exception("Цепочка %s", steps)
                return ReplyDTO(line("error", e=e))
        return self.handle_one(c)

    def handle_one(self, c: str) -> ReplyDTO | None:
        m = BROWSER_SUFFIX.search(c)
        self._context.browser_once, missing = None, None
        if m:  # «открой ютуб в хроме» — браузер только для этой команды
            if self._browser.find_browser(m.group("b")):
                self._context.browser_once = m.group("b")
            else:
                missing = next((BROWSER_NAMES[k] for p, k in BROWSER_WORDS if re.fullmatch(p, m.group("b"))),
                               m.group("b"))
            c = c[:m.start()].strip()
        try:
            r = self._route(c)
        finally:
            self._context.browser_once = None
        if r and missing:
            r.text = line("browser_missing", b=missing) + " " + r.text
        return r

    def _route(self, c: str) -> ReplyDTO | None:
        r = self._memory.custom_reply(c)  # свои ответы — раньше команд и нейросети
        if r:
            return r
        for pattern, fn in self._routes:
            m = re.search(pattern, c)
            if m:
                try:
                    r = fn(c, m)
                except Exception as e:
                    log.exception("Команда %s", c)
                    return ReplyDTO(line("error", e=e))
                if r:
                    return r
        return None

    def fallback(self, cmd: str, force_search: bool = False) -> ReplyDTO:
        return self._web.fallback(cmd, force_search)

    def stop_background(self) -> bool:
        return self._input.stop_background()

    def autoscroll_active(self) -> bool:
        return self._input.autoscroll_active()
