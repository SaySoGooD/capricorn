import difflib
import os
import re
import time
import urllib.parse

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.app_candidate_dto import AppCandidateDTO
from src.application.assistant.dto.process_dto import ProcessGroupDTO
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.fuzzy import Fuzzy
from src.application.assistant.interfaces.i_app_catalog_adapter import IAppCatalogAdapter
from src.application.assistant.interfaces.i_app_commands_usecase import IAppCommandsUseCase
from src.application.assistant.interfaces.i_file_system_adapter import IFileSystemAdapter
from src.application.assistant.interfaces.i_open_url_usecase import IOpenUrlUseCase
from src.application.assistant.interfaces.i_process_adapter import IProcessAdapter
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.persona import persona
from src.application.assistant.text import Text

ORDS = ["первое", "второе", "третье"]


class AppCommandsUseCase(IAppCommandsUseCase):
    """Программы, сайты, папки и файлы: открыть, закрыть, снять задачу, создать."""

    def __init__(
        self,
        context: CommandContext,
        catalog: IAppCatalogAdapter,
        file_system: IFileSystemAdapter,
        processes: IProcessAdapter,
        window: IWindowAdapter,
        open_url: IOpenUrlUseCase,
    ) -> None:
        self._context = context
        self._catalog = catalog
        self._file_system = file_system
        self._processes = processes
        self._window = window
        self._open_url = open_url

    # --- выбор из нескольких вариантов ---
    @staticmethod
    def resolve_choice(c: str, options: list[tuple[str, object]]) -> int | None:
        """«второе», «два», «клод», «первую» → номер варианта или None."""
        ords = [(r"перв\w*|один|одну|1", 0), (r"втор\w*|два|две|2", 1), (r"трет\w*|три|3", 2),
                (r"последн\w*", len(options) - 1)]
        for pattern, idx in ords:
            if re.search(rf"(^|\s)({pattern})(\s|$)", c) and idx < len(options):
                return idx
        words = re.sub(r"^(открой|запусти|давай|вот|это|ну)\s+", "", c)
        best, best_i = 0.0, None
        for i, (name, _) in enumerate(options):
            for v in {words, Text.translit(words)}:
                s = 1.0 if v and v in name else difflib.SequenceMatcher(None, v, name).ratio()
                if Fuzzy.sounds_like(v, name.split()[0] if name.split() else name):
                    s = max(s, 0.86)
                if s > best:
                    best, best_i = s, i
        return best_i if best >= 0.6 else None

    def answer_choice(self, c: str) -> ReplyDTO | None:
        """Ответ на «какое открыть / закрыть?». None — это не выбор, а новая команда."""
        options, self._context.choice = self._context.choice, None
        if not options:
            return None
        pick = self.resolve_choice(c, options)
        if pick is not None:
            name, act = options[pick]
            if callable(act):
                return act()
            started = self._catalog.launch_best(name, [AppCandidateDTO(1.0, name, act)])
            return ReplyDTO(persona.line("launch", t=started) if started else persona.line("app_missing", t=name))
        if re.match(r"^(никак\w*|ни одно|ни то|отмена|не надо|нет|ничего)\b", c):
            return ReplyDTO(persona.line("cancel"))
        return None

    # --- открыть ---
    def _run(self, target: str) -> None:
        if target.startswith(("http://", "https://")):
            self._open_url(target)
            return
        self._catalog.run_target(target)

    def open(self, c: str, m: re.Match) -> ReplyDTO | None:
        if re.search(r"ютуб|youtube", c):
            self._context.youtube_opened_at = time.time()  # следующее «напиши …» будет поиском на YouTube
        t = re.sub(r"^(мне |пожалуйста |программу |приложение )", "", m.group("t"))
        t = re.sub(r" пожалуйста$", "", t).strip()
        if t in ("звук",):
            return None
        site_mode = t.startswith("сайт ")
        if site_mode:
            t = t[5:].strip()
        else:
            explicit = re.match(r"^(папк\w*|каталог\w*|директори\w*)\s+(?P<n>.+)$", t)
            found = self._file_system.find_folder(explicit.group("n") if explicit else t, search=bool(explicit))
            if found:
                self._file_system.open_path(found.path)
                return ReplyDTO(persona.line("folder_open", t=found.label))
            if explicit:
                return ReplyDTO(persona.line("folder_missing", t=explicit.group("n")))

        apps, sites = self._context.apps, self._context.sites
        if not site_mode and t in apps:
            self._run(apps[t])
            return ReplyDTO(persona.line("open", t=t))

        if t in sites:
            self._open_url(sites[t])
            return ReplyDTO(persona.line("open", t=t))
        close = difflib.get_close_matches(t, list(sites), n=1, cutoff=0.82)
        if close:
            self._open_url(sites[close[0]])
            return ReplyDTO(persona.line("open", t=close[0]))

        domain = re.sub(r"\s*(точка|dot)\s*", ".", t).replace(" ", "")
        if re.fullmatch(r"[\w\-]+(\.[\w\-]+)*\.[a-zа-я]{2,}", domain):
            self._open_url("https://" + domain)
            return ReplyDTO(persona.line("open", t=domain))

        if not site_mode:
            self._catalog.wait_ready(8)
            options = self._catalog.candidates(t, self._context.aliases)
            if not options:
                # не программа и не известный сайт → трактуем «открой X» как открыть сайт X
                # и прыгаем сразу на него (не в выдачу — это делает «найди X»)
                self._open_web(t)
                return ReplyDTO(persona.line("web_site", t=t))
            top = options[0]
            similar = [o for o in options[1:] if top.score - o.score < 0.1]
            if top.score >= 1.0 or not similar:  # одно явно подходит — запускаем
                started = self._catalog.launch_best(t, [top])
                return ReplyDTO(persona.line("launch", t=started) if started else persona.line("app_missing", t=t))
            # несколько похожих — спрашиваем, какое открыть
            self._context.choice = [(o.name, o.target) for o in [top] + similar[:2]]
            listed = ", ".join(f"{ORDS[i]} — {n.title()}" for i, (n, _) in enumerate(self._context.choice))
            return ReplyDTO(persona.line("choose_app", t=listed), "ask")
        self._open_web(t)
        return ReplyDTO(persona.line("web_site", t=t))

    def _open_web(self, t: str) -> None:
        """«Открой X», когда X — не программа и не домен: открываем сам сайт.

        I'm Feeling Ducky у DuckDuckGo (префикс «\\») делает 302 сразу на первый
        результат, то есть мы попадаем на сам сайт, а не на страницу выдачи.
        «Найди X» по-прежнему открывает именно выдачу — в этом и разница.
        """
        self._open_url("https://duckduckgo.com/?q=" + urllib.parse.quote("\\" + t))

    # --- закрыть ---
    def kill_process(self, c: str, m: re.Match) -> ReplyDTO:
        """«сними задачу steam client helper», «заверши процесс хром принудительно», «кильни дискорд»."""
        t = re.sub(r"^(все |всех )?(процесс\w*|задач\w*)\s+", "", m.group("t").strip())
        return self._close(c, t, force=bool(re.search(r"принудительн|насильн|жестк|совсем", c)))

    def close(self, c: str, m: re.Match) -> ReplyDTO:
        return self._close(c, m.group("t").strip(), force=False)

    def _close(self, c: str, t: str, force: bool) -> ReplyDTO:
        force = force or bool(re.search(r"принудительн|насильн|жестк", c))
        t = re.sub(r"\s+(принудительно|насильно|жестко|совсем)$", "", t).strip()
        if re.fullmatch(r"(окно|это|это окно)", t):
            self._window.close_foreground()
            return ReplyDTO(persona.line("closed_window"))
        q = Text.norm(t)
        variants = {q, Text.translit(q)}
        if q in self._context.aliases:
            variants.add(Text.norm(self._context.aliases[q]))
        if q in self._context.apps:
            variants.add(os.path.splitext(os.path.basename(self._context.apps[q]))[0].lower())
        if self._catalog.is_ready():  # «закрой клод» → приложение Claude → процесс claude
            for cand in self._catalog.candidates(q, self._context.aliases, 2):
                variants.add(cand.name.split()[0])
        variants = {v.replace(" ", "") for v in variants if len(v.replace(" ", "")) >= 3}
        words = [w for w in Text.translit(q).split() if len(w) >= 3]  # для сравнения с описанием из диспетчера задач

        groups = self._processes.find_groups(variants, words)
        if not groups:
            return ReplyDTO(persona.line("not_running", t=t))
        top = groups[0]
        similar = [g for g in groups[1:] if top.score - g.score < 0.1]
        if top.score < 1.0 and similar:  # несколько похожих — спрашиваем, что закрыть
            self._context.choice = [(g.name, (lambda g=g: self._kill(g, force))) for g in [top] + similar[:2]]
            listed = ", ".join(f"{ORDS[i]} — {n}" for i, (n, _) in enumerate(self._context.choice))
            return ReplyDTO(persona.line("choose_close", t=listed), "ask")
        return self._kill(top, force)

    def _kill(self, group: ProcessGroupDTO, force: bool) -> ReplyDTO:
        status = self._processes.kill(group, force)
        if status == "denied":
            return ReplyDTO(persona.line("kill_denied", t=group.name))
        if status == "failed":
            return ReplyDTO(persona.line("kill_failed", t=group.name))
        return ReplyDTO(persona.line("closed", names=group.name))

    # --- создать ---
    def create(self, c: str, m: re.Match) -> ReplyDTO | None:
        what = m.group("what")
        place_m = re.search(r"\s(на|в|во)\s+(рабоч\w+ стол\w*|документ\w*|загрузк\w*|фото\w*|изображени\w*|"
                            r"картинк\w*|музык\w*|видео|папк\w* \S+)$", what)
        place, place_name = self._file_system.known_dir("desktop"), "на рабочем столе"
        if place_m:
            spot = self._file_system.find_folder(re.sub(r"^папк\w* ", "", place_m.group(2)), search=True)
            if not spot:
                return ReplyDTO(persona.line("folder_missing", t=place_m.group(2)))
            place, place_name = spot.path, f"в папке «{spot.label}»"
            what = what[:place_m.start()]
        kind = re.match(r"(нов\w+ )?(?P<kind>папк\w*|текстов\w+ файл\w*|текстов\w+ документ\w*|"
                        r"документ\w*|файл\w*|таблиц\w*)( (с )?(именем|названием))?\s*(?P<name>.*)$", what)
        if not kind:
            return None
        k, name = kind.group("kind"), kind.group("name").strip()
        ext = ""
        dot = re.search(r"\s*(точка|dot|\.)\s*(?P<e>[a-zа-я0-9]+)$", name)
        if dot:  # «файл заметки точка txt»
            ext, name = "." + Text.translit(dot.group("e")), name[:dot.start()].strip()
        if k.startswith("папк"):
            default = "Новая папка"
        elif k.startswith("таблиц"):
            default, ext = "Новая таблица", ext or ".xlsx"
        elif k.startswith("документ") and not k.startswith("текст"):
            default, ext = "Новый документ", ext or ".docx"
        else:
            default, ext = "Новый файл", ext or ".txt"
        name = re.sub(r'[<>:"/\\|?*]', "", name).strip() or default
        name = name[:1].upper() + name[1:]
        path = self._file_system.create(place, name, ext, is_folder=k.startswith("папк"))
        return ReplyDTO(persona.line("created", t=os.path.basename(path), where=place_name))
