import logging
import queue
import random
import re
import threading
import time
from typing import Any

from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.listener_dto import ListenerCallbacksDTO
from src.application.assistant.dto.reply_dto import ReplyDTO
from src.application.assistant.interfaces.i_app_catalog_adapter import IAppCatalogAdapter
from src.application.assistant.interfaces.i_assistant_session_usecase import IAssistantSessionUseCase
from src.application.assistant.interfaces.i_audio_devices_adapter import IAudioDevicesAdapter
from src.application.assistant.interfaces.i_avatar_view import IAvatarView
from src.application.assistant.interfaces.i_chat_model_adapter import IChatModelAdapter
from src.application.assistant.interfaces.i_handle_command_usecase import IHandleCommandUseCase
from src.application.assistant.interfaces.i_listener_adapter import IListenerAdapter
from src.application.assistant.interfaces.i_listener_factory import IListenerFactory
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.interfaces.i_settings_store import ISettingsStore
from src.application.assistant.interfaces.i_sound_effects_adapter import ISoundEffectsAdapter
from src.application.assistant.interfaces.i_speaker_adapter import ISpeakerAdapter
from src.application.assistant.interfaces.i_speech_refiner_adapter import ISpeechRefinerAdapter
from src.application.assistant.interfaces.i_thread_setup_adapter import IThreadSetupAdapter
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.interfaces.i_zapret_adapter import IZapretAdapter
from src.application.assistant.persona import LINES, gendered, line
from src.application.assistant.user_profile import apply_user, user_display_name
from src.application.assistant.wake_words import STOP_RE

log = logging.getLogger("capri")

# что перечитывать из config.json на лету (без перезапуска)
LIVE_KEYS = ("sites", "apps", "app_aliases", "search_when_unsure", "browser", "chatter", "replies",
             "user_name_mode", "user_name", "user_gender")


class AssistantSessionUseCase(IAssistantSessionUseCase):
    """Капри целиком: слушает, понимает команду, отвечает голосом и иногда появляется сама.
    Команды выполняются по очереди в рабочем потоке; события микрофона приходят из потока слушателя."""

    def __init__(
        self,
        settings: dict[str, Any],
        settings_error: str,
        store: ISettingsStore,
        context: CommandContext,
        handle_command: IHandleCommandUseCase,
        cloud_chat: IChatModelAdapter,
        local_chat: ILocalChatModelAdapter | None,
        speaker: ISpeakerAdapter,
        listener_factory: IListenerFactory,
        audio_devices: IAudioDevicesAdapter,
        speech_refiner: ISpeechRefinerAdapter,
        sound_effects: ISoundEffectsAdapter,
        view: IAvatarView,
        window: IWindowAdapter,
        zapret: IZapretAdapter,
        catalog: IAppCatalogAdapter,
        thread_setup: IThreadSetupAdapter,
    ) -> None:
        self._settings = settings
        self._settings_error = settings_error
        self._store = store
        self._context = context
        self._handle = handle_command
        self._cloud = cloud_chat
        self._local = local_chat
        self._speaker = speaker
        self._listener_factory = listener_factory
        self._devices = audio_devices
        self._refiner = speech_refiner
        self._sounds = sound_effects
        self._view = view
        self._window = window
        self._zapret = zapret
        self._catalog = catalog
        self._thread_setup = thread_setup

        words = sorted(settings["wake_words"], key=len, reverse=True)
        self._wake_re = re.compile(r"(^|\s)(" + "|".join(map(re.escape, words)) + r")(?=\s|$|[,.!?])",
                                   re.IGNORECASE)
        if self._local:
            self._local.set_on_model_change(self._remember_model)
        self._config_mtime = store.modified_time()
        self._zapret_checked = False  # предлагали ли уже исправить zapret в этом сеансе
        self._jobs: queue.Queue = queue.Queue()
        self._awake_until = 0.0
        self._last_partial_wake = 0.0
        self._speaking = False
        self._interrupted = False
        self._speech_words: set[str] = set()
        self._speech_end = 0.0
        self._last_activity = time.time()
        self._recent_chatter: list[str] = []
        self._listener: IListenerAdapter | None = None
        self._sounds.prepare_glitch(self._speaker.volume)

    # ----- запуск -----
    @property
    def settings(self) -> dict[str, Any]:
        return self._settings

    @property
    def listener(self) -> IListenerAdapter | None:
        return self._listener

    def start(self) -> None:
        apply_user(self._settings)
        self._catalog.start_indexing()
        threading.Thread(target=self._worker, daemon=True).start()
        if self._local:
            threading.Thread(target=self._local.start_server, daemon=True).start()
        if not self._listener_factory.model_exists():
            self._jobs.put(("say", line("no_model")))
            return
        self._listener = self._listener_factory.create(
            ListenerCallbacksDTO(on_final=self.on_final, on_partial=self.on_partial, on_error=self.on_listener_error),
            device_name=self._settings.get("mic_device") or None,
            gain=float(self._settings.get("mic_gain", 1.0)),
            sensitivity=int(self._settings.get("mic_sensitivity", 100)),
        )
        self._listener.start()
        # вступление: анимация capri + приветствие
        self._jobs.put(("say", line("greet") if self._settings.get("greet_on_start") else "", "capri"))
        if self._settings_error:
            self._jobs.put(("say", self._settings_error))
        threading.Thread(target=self._chatter_loop, daemon=True).start()  # сам проверяет, включено ли
        threading.Thread(target=self._prewarm_voice, daemon=True).start()

    def _prewarm_voice(self) -> None:
        """Через полминуты после запуска озвучиваем в фоне постоянные фразы и свои ответы — потом они
        звучат сразу, без ожидания сервера Microsoft."""
        time.sleep(30)
        static = [gendered(t) for variants in LINES.values() for t in variants if "{" not in t]
        static += list(self._settings.get("replies", {}).values())
        self._speaker.prewarm(static)

    # ----- спонтанные появления -----
    def _chatter_loop(self) -> None:
        def next_delay() -> float:
            lo, hi = self._settings["chatter_min_minutes"], self._settings["chatter_max_minutes"]
            return random.uniform(lo, max(lo, hi)) * 60
        due = time.time() + next_delay()
        while True:
            time.sleep(15)
            now = time.time()
            if not self._settings.get("chatter"):  # выключено галочкой в трее — ждём, отсчёт начнётся заново
                due = now + next_delay()
                continue
            if now < due:
                continue
            quiet = now - self._last_activity > 120 and self._jobs.empty() and not self._speaking
            if quiet and not self._window.fullscreen_app_active():
                self._jobs.put(("chatter",))
                due = now + next_delay()
            else:
                due = now + 60  # занят или в игре/фильме — попробуем позже

    def _chatter_line(self) -> str:
        hour = time.localtime().tm_hour
        text = None
        if 0 <= hour < 5 and random.random() < 0.5:
            text = line("chatter_night")
        elif 6 <= hour < 11 and random.random() < 0.3:
            text = line("chatter_morning")
        elif self._local and random.random() < 0.4:
            text = self._local.chatter()
        for _ in range(5):
            if text and text not in self._recent_chatter:
                break
            text = line("chatter")
        self._recent_chatter = (self._recent_chatter + [text])[-6:]
        return text

    # ----- события микрофона (поток слушателя) -----
    def _has_wake(self, text: str) -> bool:
        return bool(self._wake_re.search(text.lower()))

    def _strip_wake(self, text: str) -> str:
        t = text.lower()
        matches = list(self._wake_re.finditer(t))
        last = matches[-1] if matches else None
        if last and t[last.end():].strip(" ,.!?"):
            t = t[last.end():]  # берём то, что сказано после имени (до него могло быть эхо)
        t = self._wake_re.sub(" ", t)
        return re.sub(r"^[\s,.!?]+|[\s,.!?]+$", "", t)

    def _appear(self, seconds: float) -> None:
        self._sounds.play_glitch()
        self._view.summon()
        self._view.set_mode("listening", float(seconds))

    def _is_echo(self, text: str) -> bool:
        """Микрофон слышит голос самой Капри: все слова фразы есть в том, что она говорит."""
        words = text.lower().replace("ё", "е").split()
        return bool(words) and all(w in self._speech_words for w in words)

    def _wants_interrupt(self, text: str) -> bool:
        t = text.lower()
        return bool(self._has_wake(t) or STOP_RE.search(t)) and not self._is_echo(t)

    def interrupt(self) -> None:
        if not self._speaking or self._interrupted:
            return
        self._interrupted = True
        self._speaker.stop()
        self._awake_until = time.time() + self._settings["listen_window_seconds"]
        self._view.set_mode("listening", float(self._settings["listen_window_seconds"]))
        self._view.set_subtitle(line("listen"))
        log.info("Капри перебили")

    def on_partial(self, text: str) -> None:
        now = time.time()
        if self._speaking:
            if self._settings.get("barge_in") and self._wants_interrupt(text):
                self.interrupt()
            return
        if now - self._last_partial_wake > 3 and now > self._awake_until and self._has_wake(text):
            self._last_partial_wake = now
            self._appear(self._settings["listen_window_seconds"])

    def on_final(self, text: str, audio: bytes) -> None:
        now = time.time()
        listen = self._settings["listen_window_seconds"]
        if self._handle.autoscroll_active() and STOP_RE.search(text.lower()) and not self._is_echo(text):
            # во время автопрокрутки «стоп» слышим и без имени
            self._handle.stop_background()
            self._view.set_subtitle(line("scroll_stop"))
            return
        if self._speaking and not self._interrupted:
            if not (self._settings.get("barge_in") and self._wants_interrupt(text)):
                return  # эхо собственной речи
            self.interrupt()
        if now - self._speech_end < 1.0 and self._is_echo(text):
            return
        woke = self._has_wake(text)
        if not woke and now > self._awake_until:
            return
        cmd = self._strip_wake(text) if woke else text
        if STOP_RE.match(cmd.strip()) and len(cmd.split()) <= 3:
            # «Капри, стоп» — замолчать, остановить автопрокрутку и слушать дальше
            self._awake_until = now + listen
            if self._handle.stop_background():
                self._view.set_subtitle(line("scroll_stop"))
            return
        if len(cmd) < 2:
            self._awake_until = now + listen
            self._view.set_subtitle("")
            if now - self._last_partial_wake > 3:
                self._appear(listen)
            return
        self._awake_until = 0
        self._jobs.put(("voice", cmd, audio, woke))

    def on_listener_error(self, err: Any, kind: str = "mic") -> None:
        self._jobs.put(("say", line("model_broken" if kind == "model" else "no_mic")))

    # ----- настройки из трея и окон -----
    def set_profile(self, mode: str, name: str, gender: str) -> None:
        """«Как ко мне обращаться…»: как называть пользователя и в каком роде. Сразу и запоминается."""
        for key, value in (("user_name_mode", mode), ("user_name", name), ("user_gender", gender)):
            self._settings[key] = value
            self._store.save_setting(key, value)
        apply_user(self._settings)
        log.info("Обращение: %s, %s", user_display_name(self._settings) or "без имени", gender)

    def _set_flag(self, key: str, on: bool, what: str) -> None:
        self._settings[key] = bool(on)
        self._store.save_setting(key, bool(on))
        log.info("%s: %s", what, "включено" if on else "выключено")

    def set_chatter(self, on: bool) -> None:
        """Появляется ли Капри сама (поболтать, погулять по экрану)."""
        self._set_flag("chatter", on, "Самостоятельные появления")

    def set_search_when_unsure(self, on: bool) -> None:
        """Открывать ли Google, когда Капри не знает ответа."""
        self._set_flag("search_when_unsure", on, "Поиск в браузере, если не знаю")

    def _remember_model(self, name: str) -> None:
        """Ollama нашла другую скачанную модель — записываем её, чтобы не искать при каждом запуске."""
        self._settings["local_model"] = name
        self._store.save_setting("local_model", name)

    def reload_settings_if_changed(self, speak: bool = True) -> None:
        """Правки config.json (сайты, программы, названия) подхватываются без перезапуска.
        speak=False — из окна в трее: там говорить нельзя (речь блокирует окно)."""
        mtime = self._store.modified_time()
        if mtime == self._config_mtime:
            return
        fresh = self._store.load()
        if fresh.error:  # с ошибкой — работаем как было и говорим, где ошибка
            if speak:
                self._config_mtime = mtime
                self.say(fresh.error)
            return
        self._config_mtime = mtime
        for key in LIVE_KEYS:
            self._settings[key] = fresh.settings[key]
        self._context.set_lists(self._settings)
        apply_user(self._settings)
        log.info("config.json перечитан")

    # ----- микрофон и голос -----
    def current_mic(self) -> str:
        if self._listener and self._listener.active_name:
            return self._listener.active_name
        return self._settings.get("mic_device") or self._devices.default_input_name()

    def input_devices(self) -> list[str]:
        return self._devices.input_devices()

    def default_input_name(self) -> str:
        return self._devices.default_input_name()

    def set_mic(self, name: str | None, announce: bool = True) -> None:
        """Сменить устройство ввода на ходу и запомнить выбор (None — как в Windows по умолчанию)."""
        self._settings["mic_device"] = name
        self._store.save_setting("mic_device", name)
        if self._listener:
            self._listener.set_device(name)
        log.info("Выбран микрофон: %s", name or "по умолчанию")
        if announce:
            self._jobs.put(("say", line("mic_set", t=name or "микрофон Windows по умолчанию")))

    def set_mic_tuning(self, gain: float | None = None, sensitivity: int | None = None) -> None:
        """Громкость ввода и чувствительность микрофона для Капри — сразу и запоминаются."""
        if gain is not None:
            self._settings["mic_gain"] = round(float(gain), 2)
            self._store.save_setting("mic_gain", self._settings["mic_gain"])
            if self._listener:
                self._listener.gain = self._settings["mic_gain"]
        if sensitivity is not None:
            self._settings["mic_sensitivity"] = int(sensitivity)
            self._store.save_setting("mic_sensitivity", self._settings["mic_sensitivity"])
            if self._listener:
                self._listener.sensitivity = self._settings["mic_sensitivity"]

    def set_voice_fx(self, strength: float) -> None:
        """Сила цифровых эффектов голоса: 0 — чистый голос, 1.8 — как задумано, больше — сильнее."""
        self._speaker.fx = round(float(strength), 2)
        self._settings["voice_fx"] = self._speaker.fx
        self._store.save_setting("voice_fx", self._speaker.fx)

    def set_voice_volume(self, volume: int) -> None:
        """Громкость голоса Капри 0..100 — только её, общая громкость Windows не меняется."""
        self._speaker.volume = int(volume)
        self._settings["voice_volume"] = int(volume)
        self._store.save_setting("voice_volume", int(volume))
        self._sounds.prepare_glitch(self._speaker.volume)

    def _mic_command(self, action: str) -> ReplyDTO:
        if action == "mic_info":
            return ReplyDTO(line("mic_info", t=self.current_mic()))
        devices = self._devices.input_devices()
        if len(devices) < 2:
            return ReplyDTO(line("mic_only_one", t=self.current_mic()))
        cur = self._settings.get("mic_device") or self.current_mic()
        idx = next((i for i, n in enumerate(devices) if n == cur or cur.startswith(n) or n.startswith(cur)), -1)
        nxt = devices[(idx + 1) % len(devices)]
        self.set_mic(nxt, announce=False)
        return ReplyDTO(line("mic_set", t=nxt))

    # ----- ввод не голосом -----
    def call_from_click(self) -> None:
        if self._speaking:
            self.interrupt()
            return
        self._awake_until = time.time() + self._settings["listen_window_seconds"]
        self._appear(self._settings["listen_window_seconds"])
        self._view.set_subtitle(line("listen"))

    def text_command(self, text: str) -> None:
        self._view.summon()
        self._jobs.put(("text", text))

    def say_later(self, text: str) -> None:
        """Сказать в рабочем потоке (не блокируя окно, из которого попросили)."""
        self._jobs.put(("say", text))

    # ----- рабочий поток -----
    def _worker(self) -> None:
        self._thread_setup.prepare_worker_thread()
        while True:
            job = self._jobs.get()
            try:
                self._process(job)
            except Exception:
                log.exception("Ошибка обработки %s", job[0])
                self.say(line("crash"))

    def _process(self, job: tuple) -> None:
        kind = job[0]
        view = self._view
        if kind == "chatter":
            text = self._chatter_line()
            if random.random() < self._settings.get("roam_chance", 0.5):
                view.roam()          # гуляет по экрану, окно с текстом сверху
                time.sleep(1.5)
            else:
                view.summon()
            if not self.say(text):
                view.set_mode("idle", 0.0)
            return
        self._last_activity = time.time()
        if kind == "say":
            view.summon()
            if len(job) > 2:
                view.play_anim(job[2])
            if not job[1] or not self.say(job[1]):
                view.set_mode("idle", 0.0)
            return
        if kind == "voice":
            _, cmd, audio, woke = job
            view.summon()
            view.set_mode("thinking", 0.0)
            view.set_subtitle("> " + cmd)
            if self._settings.get("use_google_stt"):
                better = self._refiner.refine(audio)
                if better and len(better.lower()) >= 2:
                    cmd = better.lower()
        else:
            cmd = job[1]
        listen = float(self._settings["listen_window_seconds"])
        if self._has_wake(cmd):
            # имя могло остаться в тексте («капри нажми …»), если Капри уже слушала без него
            stripped = self._strip_wake(cmd)
            if len(stripped) < 2:
                # просто позвали по имени — не болтаем, а слушаем
                self._awake_until = time.time() + listen
                view.set_mode("listening", listen)
                view.set_subtitle(line("listen"))
                return
            cmd = stripped
        log.info("Команда: %s", cmd)
        view.set_mode("thinking", 0.0)
        view.set_subtitle("> " + cmd)
        self.reload_settings_if_changed()

        reply = self._handle(cmd)
        if reply is not None and reply.action in ("mic_info", "mic_next"):
            reply = self._mic_command(reply.action)
        if reply is None:
            if self._settings.get("enable_ai") and self._cloud.available:
                reply = ReplyDTO(self._cloud.ask(cmd), "answer")
            else:
                answer = self._local.ask(cmd) if self._local else None
                reply = ReplyDTO(answer, "answer") if answer else self._handle.fallback(
                    cmd, force_search=bool(self._local))
        if reply.action == "answer" and self._settings.get("teleport_on_answer"):
            view.hop()  # отвечает, скача по экрану красной молнией
        if reply.action == "wave":
            view.play_anim("capri")
        elif reply.action and reply.action.startswith("move:"):
            view.move_to(reply.action[5:])
        elif reply.action == "roam":
            view.vanish()
            time.sleep(0.8)
            view.roam()
            time.sleep(1.5)
        if self.say(reply.text):
            return  # перебили — уже слушаем новую команду

        if reply.action == "quit":
            view.quit_app()
        elif reply.action == "hide":
            view.vanish()
        else:
            follow = float(self._settings["followup_seconds"])
            self._awake_until = time.time() + follow
            view.set_mode("listening", follow)

    def say(self, text: str) -> bool:
        """Озвучивает текст. Возвращает True, если Капри перебили."""
        log.info("Капри: %s", text)
        self._view.set_subtitle(text)
        self._view.set_mode("speaking", 0.0)
        listener = self._listener
        barge_in = bool(self._settings.get("barge_in") and listener)
        if listener and not barge_in:
            listener.mute()
        self._speech_words = set(re.findall(r"\w+", text.lower().replace("ё", "е")))
        self._interrupted = False
        self._speaking = True
        try:
            self._speaker.say(text)
        finally:
            self._speaking = False
            self._speech_end = time.time()
            if barge_in and not self._interrupted:
                listener.reset_recognition()  # выбрасываем эхо её голоса
            if listener and not barge_in:
                time.sleep(0.25)
                listener.unmute()
        self._check_voice_blocked()
        return self._interrupted

    def _check_voice_blocked(self) -> None:
        """Голос Microsoft не прошёл из-за сети, а запущен zapret — один раз за сеанс объясняем
        и предлагаем добавить сервер голоса в исключения zapret."""
        err = self._speaker.last_error
        z = self._zapret
        if self._zapret_checked or not err or not z.is_network_error(err) or not z.running():
            return
        self._zapret_checked = True
        all_lists = z.find_all_lists()
        todo = [lst for lst in all_lists if not z.excluded(lst)]
        if not all_lists:
            self._jobs.put(("say", line("zapret_manual")))
        elif not todo:
            self._jobs.put(("say", line("zapret_restart")))
        else:
            def fix() -> ReplyDTO:
                try:
                    for lst in todo:  # во все найденные копии zapret — какая из них запущена, не видно
                        z.add_exclude(lst)
                        log.info("Сервер голоса добавлен в исключения zapret (имя и адреса): %s", lst)
                except OSError as e:
                    log.exception("Не удалось дописать исключение zapret")
                    return ReplyDTO(line("zapret_fail", e=e))
                return ReplyDTO(line("zapret_fixed"))
            self._context.pending = fix
            self._awake_until = time.time() + 20  # ответ «да» без имени
            self._jobs.put(("say", line("zapret_offer")))
