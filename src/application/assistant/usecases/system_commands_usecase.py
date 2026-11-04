import re

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_chat_model_adapter import IChatModelAdapter
from src.application.assistant.interfaces.i_diagnostics_adapter import IDiagnosticsAdapter
from src.application.assistant.interfaces.i_display_adapter import IDisplayAdapter
from src.application.assistant.interfaces.i_file_system_adapter import IFileSystemAdapter
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.interfaces.i_power_adapter import IPowerAdapter
from src.application.assistant.interfaces.i_process_adapter import IProcessAdapter
from src.application.assistant.interfaces.i_screenshot_adapter import IScreenshotAdapter
from src.application.assistant.interfaces.i_system_audio_adapter import ISystemAudioAdapter
from src.application.assistant.interfaces.i_system_commands_usecase import ISystemCommandsUseCase
from src.application.assistant.persona import line
from src.application.assistant.text import parse_number


class SystemCommandsUseCase(ISystemCommandsUseCase):
    """Компьютер: питание, блокировка, громкость, яркость, диагностика, скриншот, тяжёлые процессы."""

    def __init__(
        self,
        context: CommandContext,
        power: IPowerAdapter,
        audio: ISystemAudioAdapter,
        display: IDisplayAdapter,
        diagnostics: IDiagnosticsAdapter,
        file_system: IFileSystemAdapter,
        screenshot: IScreenshotAdapter,
        processes: IProcessAdapter,
        cloud_chat: IChatModelAdapter,
        local_chat: ILocalChatModelAdapter | None,
    ) -> None:
        self._context = context
        self._power = power
        self._audio = audio
        self._display = display
        self._diagnostics = diagnostics
        self._file_system = file_system
        self._screenshot = screenshot
        self._processes = processes
        self._cloud_chat = cloud_chat
        self._local_chat = local_chat

    def power(self, c: str, m: re.Match) -> ReplyDTO:
        restart = m.group(1).startswith("перезаг") or m.group(1).startswith("перезап")

        def do() -> ReplyDTO:
            self._power.shutdown(restart)
            return ReplyDTO(line("power_do", what_noun="перезагрузка" if restart else "выключение"))
        self._context.pending = do
        verb = "перезагрузить" if restart else "выключить"
        return ReplyDTO(line("power_ask", what=verb, what_cap=verb.capitalize()))

    def lock(self, c: str, m: re.Match) -> ReplyDTO:
        self._power.lock()
        return ReplyDTO(line("lock"))

    def volume(self, c: str, m: re.Match) -> ReplyDTO:
        if re.search(r"(выключи|выключить|отключи|убери|убрать)\w* звук|без звука|замуть", c):
            self._audio.set_mute(True)
            return ReplyDTO(line("mute"))
        if re.search(r"(включи|включить|верни)\w* звук", c) and parse_number(c) is None:
            self._audio.set_mute(False)
            return ReplyDTO(line("unmute"))
        n = parse_number(c)
        cur = self._audio.get_volume()
        if re.search(r"громче|прибав|увелич|повыс|выше", c):
            new = cur + (n or 10)
        elif re.search(r"тише|убав|уменьш|пониз|ниже", c):
            new = cur - (n or 10)
        elif n is not None:
            new = n
        else:
            return ReplyDTO(line("vol_now", n=cur))
        new = max(0, min(100, new))
        self._audio.set_volume(new)
        return ReplyDTO(line("vol_set", n=new))

    def brightness(self, c: str, m: re.Match) -> ReplyDTO:
        try:
            cur = self._display.get_brightness()
        except Exception:
            return ReplyDTO(line("bright_fail"))
        n = parse_number(c)
        if re.search(r"ярче|прибав|увелич|повыс|выше", c):
            new = cur + (n or 15)
        elif re.search(r"темнее|убав|уменьш|пониз|ниже", c):
            new = cur - (n or 15)
        elif n is not None:
            new = n
        else:
            return ReplyDTO(line("bright_now", n=cur))
        new = max(0, min(100, new))
        try:
            self._display.set_brightness(new)
        except Exception:
            return ReplyDTO(line("bright_reject"))
        return ReplyDTO(line("bright_set", n=new))

    def analyze(self, c: str, m: re.Match) -> ReplyDTO:
        result = self._diagnostics.analyze()
        self._file_system.open_path(self._file_system.save_report(result.report))
        use_cloud = self._context.settings.get("enable_ai") and self._cloud_chat.available
        spoken = self._cloud_chat.summarize_report(result.report) if use_cloud else None
        if not spoken and self._local_chat:
            spoken = self._local_chat.summarize_report(result.report)
        if spoken:
            return ReplyDTO(spoken)
        if not result.issues:
            return ReplyDTO(line("scan_ok"))
        head = "; ".join(result.issues[:4])
        return ReplyDTO(line("scan_bad", n=len(result.issues), head=head))

    def screenshot(self, c: str, m: re.Match) -> ReplyDTO:
        self._screenshot.capture()
        return ReplyDTO(line("screenshot"))

    def top_processes(self, c: str, m: re.Match) -> ReplyDTO:
        """«Что грузит компьютер» — три процесса, которые больше всего едят процессор и память."""
        top = self._processes.top_usage(3)
        c_txt = ", ".join(f"{p.name} {p.value:.0f} процентов" for p in top.cpu if p.value >= 1) \
            or "ничего особо не грузит"
        m_txt = ", ".join(f"{p.name} {p.value / 1024:.1f} гигабайта" if p.value >= 1024 else
                          f"{p.name} {p.value:.0f} мегабайт" for p in top.memory)
        return ReplyDTO(line("top_procs", cpu=c_txt, mem=m_txt))
