import logging
import re
from collections.abc import Callable

from src.application.assistant.browsers import BROWSER_NAMES, BROWSER_SUFFIX, BROWSER_WORDS
from src.application.assistant.command_chain import CommandChain
from src.application.assistant.command_context import CommandContext
from src.application.assistant.commands import FORGET_RE, FORGET_REPLY_RE, REMEMBER_RE, REPLY_RE, UPDATES_RE
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_app_commands_usecase import IAppCommandsUseCase
from src.application.assistant.interfaces.i_avatar_commands_usecase import IAvatarCommandsUseCase
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter
from src.application.assistant.interfaces.i_browser_automation_usecase import IBrowserAutomationUseCase
from src.application.assistant.interfaces.i_handle_command_usecase import IHandleCommandUseCase
from src.application.assistant.interfaces.i_image_generation_usecase import IImageGenerationUseCase
from src.application.assistant.interfaces.i_input_commands_usecase import IInputCommandsUseCase
from src.application.assistant.interfaces.i_media_commands_usecase import IMediaCommandsUseCase
from src.application.assistant.interfaces.i_memory_commands_usecase import IMemoryCommandsUseCase
from src.application.assistant.interfaces.i_messenger_commands_usecase import IMessengerCommandsUseCase
from src.application.assistant.interfaces.i_run_chain_usecase import IRunChainUseCase
from src.application.assistant.interfaces.i_self_knowledge_usecase import ISelfKnowledgeUseCase
from src.application.assistant.interfaces.i_system_commands_usecase import ISystemCommandsUseCase
from src.application.assistant.interfaces.i_web_commands_usecase import IWebCommandsUseCase
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.persona import persona
from src.application.assistant.text import Text

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
    image: IImageGenerationUseCase,
    self_knowledge: ISelfKnowledgeUseCase,
    browser_auto: IBrowserAutomationUseCase,
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
        # --- свой браузер Капри (CDP): раньше apps.open/close и input.click, иначе уйдёт в запуск программ ---
        (r"^(запусти|открой|включи|подними)\s+(свой|собственный)\s+браузер$|"
         r"^(запусти|подними)\s+браузер$", browser_auto.open_browser),
        (r"^(закрой|выключи|погаси|заверши)\s+(свой\s+)?браузер$", browser_auto.close_browser),
        (r"(собери данные|собери инфу|прочит\w* страниц\w*|считай страниц\w*|что на (этой )?странице|"
         r"перескажи страниц\w*|что тут написано на странице)", browser_auto.read_page),
        (r"(какие (тут |здесь )?ссылки|покажи ссылки|список ссылок|какие ссылки на странице)",
         browser_auto.list_links),
        (r"(перейди|кликни|нажми|жми|открой|тыкни)\s+по\s+ссылке\s+(?P<q>.+)$", browser_auto.click_link),
        (r"(открой|зайди на|перейди на|загрузи|зайди в)\s+(?P<q>.+?)\s+в\s+(сво[её]м|твоём)\s+браузере$",
         browser_auto.open_site),
        (r"^в\s+сво[её]м\s+браузере\s+(открой|зайди на|перейди на|загрузи)\s+(?P<q>.+)$", browser_auto.open_site),
        # --- вопросы о самой себе по своему коду (RAG) ---
        (r"что.{0,12}(у тебя )?(в|во)\s+(rag|раг|базе знаний|векторной базе|индексе|своём индексе)|"
         r"что ты (про себя )?проиндексир\w*|что в тво[её]м (rag|раг|индексе)", self_knowledge.rag_info),
        (r"(под капотом|как ты устроен\w*|из чего ты (сделан\w*|состоишь)|тво[её] (исходный )?код|"
         r"в тво[её]м коде|в твоих (исходниках|файлах)|на ч[её]м ты (написан\w*|сделан\w*)|"
         r"(расскажи|объясни)\w*.{0,20}(о сво[её]м коде|про свой код|как ты работаешь|что у тебя внутри))",
         self_knowledge.explain),
        # «как у тебя работает/устроен/подбираешь … X» — self-ссылка обязательна, иначе «как работает
        # фотосинтез» ушло бы в RAG. Глаголы — только про реализацию, чтоб не ловить болтовню.
        (r"как (у тебя|ты|тво[её]|в тебе) (работает|работаешь|сделан\w*|реализован\w*|устроен\w*|написан\w*|"
         r"подбира\w*|выбира\w*|генери\w*|храни\w*|обрабат\w*|запуска\w*|реша\w*|определя\w*)\s+(?P<q>.+)",
         self_knowledge.explain),
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
        # клик по элементу окна (кнопка/ссылка/пункт) — раньше нажатия клавиш, иначе «нажми на …» уйдёт в клавиши
        (r"^(кликни|клик|клацни|ткни)( по| на)? (?P<name>.+)$", input.click),
        (r"^(нажми|нажать|жми|нажмите)( на| по)? (?:кнопк\w*|кнопке|ссылк\w*|ссылке|пункт\w*|элемент\w*|"
         r"поле|галочк\w*|чекбокс\w*|переключател\w*) (?P<name>.+)$", input.click),
        (r"^(нажми|нажать|зажми|жми|набери сочетание) (?P<k>.+)$", input.press),
        (rf"^({CommandChain.TYPE_VERBS})\s+\S", input.type_cmd),
        (r"^(открой |зайди в |перейди в |выбери |найди )?(в )?(телеграм\w*|telegram|телег\w*|тг )?\s*"
         r"((?P<ord>{}) )?(чат\w*|chat|диалог\w*|переписк\w*|контакт\w*|беседу|беседа|группу|канал)"
         r"( с| со)?( (?P<name>.+))?$".format("|".join(CommandChain.ORDINALS)), messenger.chat),
        # «открой телеграм папа» — запустить Telegram и сразу открыть чат с этим именем
        (r"^(открой|зайди в|перейди в|напиши в|запусти) (телеграм\w*|telegram|телег\w*|тг) (?P<name>(?!и |"
         r"напиши|первый|второй|третий).+)$", messenger.chat),
        (r"сверни (все|всё)|покажи рабочий стол", input.minimize_all),
        (r"\bсверни\b", input.minimize),
        (r"(закрой|закрыть|убери) (эту |текущую |\S+ )?вкладк", input.tab),
        (r"нов(ую|ая) вкладк|\b(верни|восстанови) (закрыт\w* )?вкладк|(следующ|предыдущ)\w* вкладк", input.tab),
        # переключение на вкладку по номеру: «первую вкладку», «перейди на вкладку 2», «последнюю вкладку»
        (r"(перв\w*|втор\w*|трет\w*|четв[её]рт\w*|пят\w*|шест\w*|седьм\w*|восьм\w*|девят\w*|десят\w*|последн\w*|\d+)"
         r"(?:-\w+)?\s+вкладк\w*|вкладк\w*\s+(?:номер\s+)?"
         r"(перв\w*|втор\w*|трет\w*|четв[её]рт\w*|пят\w*|шест\w*|седьм\w*|восьм\w*|девят\w*|десят\w*|последн\w*|\d+)",
         input.switch_tab),
        (r"^(создай|сделай|создать) (?P<what>.*(папк|файл|документ|таблиц).*)$", apps.create),
        # управление сервером ComfyUI — раньше apps.open/close, иначе «запусти/закрой» уйдёт в запуск программ
        (r"^(запусти|запустить|включи|включить|подними|поднять|врубай|вруби|стартани|открой)\s+"
         r"(comfyui|comfy\w*|комфи\w*|комфиюай)$", image.start_server),
        (r"^(выключи|выключить|выгрузи|выгрузить|офни|закрой|закрыть|заверши|останови|убей|погаси|вырубай|выруби)\s+"
         r"(comfyui|comfy\w*|комфи\w*|комфиюай)$", image.stop_server),
        # генерация картинки локальным ComfyUI — раньше поиска картинок («нарисуй», а не «найди»)
        (r"^(?:(?:нарисуй|нарисуешь|рисуй|сгенерируй|сгенери\w*|генерируй|изобрази|намалюй)|"
         r"(?:сделай|создай) (?:мне |нам )?(?:картинк\w*|изображени\w*|рисунок|рисунки|арт|пикч\w*)"
         r"(?: (?:с|со|про|о|об|на тему|где|на которой))?)"
         r"\s+(?:мне |нам )?(?P<q>.+)$", image.draw),
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
        # «открой/покажи/глянь X в гугле/в поиске/в интернете» — это веб-поиск, а не запуск программы;
        # обязательно до apps.open, иначе «открой …» уйдёт в поиск установленных приложений
        (r"^(открой|откройка|покажи|глянь|глянька|посмотри|найди|поищи)( мне)?\s+(?P<q>.+?)\s+"
         r"(в гугле|в гугл|в google|гуглом|через гугл|в поиске|в интернете|в сети)$", web.search),
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
        image: IImageGenerationUseCase,
        self_knowledge: ISelfKnowledgeUseCase,
        browser_auto: IBrowserAutomationUseCase,
    ) -> None:
        self._context = context
        self._browser = browser
        self._youtube = youtube
        self._run_chain = run_chain
        self._memory = memory
        self._input = input
        self._apps = apps
        self._web = web
        self._routes = build_routes(avatar, memory, system, input, media, messenger, apps, web, image,
                                    self_knowledge, browser_auto)

    def __call__(self, cmd: str) -> ReplyDTO | None:
        c = Text.norm(cmd)
        self._youtube.cancel_ensure()  # новая команда — старая проверка «заиграло ли видео» больше не нужна
        ctx = self._context
        if ctx.pending:
            action, ctx.pending = ctx.pending, None
            if re.match(r"^(да|давай|подтверждаю|конечно|ага)\b", c):
                return action()
            if re.match(r"^(нет|не надо|отмена|стоп)\b", c):
                return ReplyDTO(persona.line("cancel"))
        # любая новая команда останавливает автопрокрутку; «стоп» на этом и заканчивается
        stopped = self._input.stop_background()
        if stopped and re.match(r"^(стоп|хватит|стой|остановись|достаточно|перестань|харэ|все|всё)\b", c):
            return ReplyDTO(persona.line("scroll_stop"))
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
        steps = None if whole else CommandChain.split_chain(c)
        if steps:
            try:
                return self._run_chain(steps, self.handle_one)
            except Exception as e:
                log.exception("Цепочка %s", steps)
                return ReplyDTO(persona.line("error", e=e))
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
            r.text = persona.line("browser_missing", b=missing) + " " + r.text
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
                    return ReplyDTO(persona.line("error", e=e))
                if r:
                    return r
        return None

    def fallback(self, cmd: str, force_search: bool = False) -> ReplyDTO:
        return self._web.fallback(cmd, force_search)

    def stop_background(self) -> bool:
        return self._input.stop_background()

    def autoscroll_active(self) -> bool:
        return self._input.autoscroll_active()
