"""Распознавание речи с микрофона офлайн (Vosk)."""
import contextlib
import json
import logging
import os
import queue
import shutil
import tempfile
import threading
import time

from src.application.assistant.audio_levels import GATE_MAX

log = logging.getLogger("capri")


RATE = 16000


def _model_complete(folder):
    return os.path.isfile(os.path.join(folder, "am", "final.mdl"))


def ascii_model_path(path):
    """Vosk не открывает пути с кириллицей (ошибка «синтаксическая ошибка в имени файла») — копируем
    модель туда, где путь латиницей. Если и имя пользователя Windows русское, его папки не подходят,
    поэтому дальше пробуем общие папки C:\\ProgramData и C:\\Users\\Public."""
    if path.isascii():
        return path
    bases = [os.environ.get("LOCALAPPDATA", ""), os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
             os.environ.get("PUBLIC", r"C:\Users\Public"), tempfile.gettempdir()]
    for base in bases:
        target = os.path.join(base, "Capri", os.path.basename(path.rstrip("\\/")))
        if not base or not target.isascii():
            continue
        try:
            if not _model_complete(target):  # копия могла оборваться в прошлый раз
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(path, target)
            log.info("Модель распознавания скопирована в %s (в исходном пути есть кириллица)", target)
            return target
        except OSError as e:
            log.info("Не удалось скопировать модель в %s: %s", target, e)
    return path


def input_devices():
    """Устройства ввода [(название, индекс)] — по одному на микрофон, как в настройках звука Windows."""
    import sounddevice as sd
    apis = sd.query_hostapis()
    mme = next((i for i, a in enumerate(apis) if "MME" in a["name"]), None)
    out, seen = [], set()
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] <= 0 or (mme is not None and d["hostapi"] != mme):
            continue
        name = d["name"].strip()
        low = name.lower()
        if "sound mapper" in low or "переназначение звуковых" in low or "первичный драйвер" in low:
            continue  # служебные «устройства по умолчанию»
        if name not in seen:
            seen.add(name)
            out.append((name, i))
    return out


def default_input_name():
    try:
        import sounddevice as sd
        return sd.query_devices(kind="input")["name"].strip()
    except Exception:
        return "неизвестно"


def resolve_device(name):
    """Индекс устройства по сохранённому названию (или None — микрофон Windows по умолчанию)."""
    if not name:
        return None
    devices = input_devices()
    for n, i in devices:
        if n == name:
            return i
    for n, i in devices:  # название могло обрезаться или чуть измениться
        if name.lower()[:20] in n.lower() or n.lower()[:20] in name.lower():
            return i
    log.info("Микрофон «%s» не найден, беру микрофон по умолчанию", name)
    return None


def _refresh_devices(sd):
    """Перечитать список звуковых устройств (PortAudio запоминает его при старте)."""
    try:
        sd._terminate()
        sd._initialize()
    except Exception:
        log.exception("Не удалось обновить список устройств")


LEVEL_SCALE = 6.0  # громкость для индикатора: обычная речь у микрофона даёт примерно половину шкалы


class Listener(threading.Thread):
    """Постоянно слушает микрофон. on_final(text, audio_bytes) — законченная фраза,
    on_partial(text) — промежуточный результат (для быстрой реакции на имя).
    Микрофон можно сменить на ходу через set_device()."""

    def __init__(self, model_path, on_final, on_partial, on_error, device_name=None, gain=1.0, sensitivity=100):
        super().__init__(daemon=True)
        self.model_path = model_path
        self.on_final = on_final
        self.on_partial = on_partial
        self.on_error = on_error
        self.device_name = device_name  # None — микрофон Windows по умолчанию
        self.active_name = None         # какой микрофон реально открыт
        self.muted = threading.Event()
        self.reset_req = threading.Event()  # сбросить распознавание (отбросить эхо голоса Капри)
        self.switch = threading.Event()     # переоткрыть поток с другим микрофоном
        self.gain = gain                # громкость ввода для Капри: 1 — как есть, 2 — вдвое громче
        self.sensitivity = sensitivity  # 100 — слышит всё, меньше — тихие звуки (шум, фон) отбрасываются
        self.level = 0.0                # текущая громкость с микрофона 0..1 — для индикатора в настройках

    def set_device(self, name):
        self.device_name = name or None
        self.switch.set()

    def gate_level(self):
        """Порог громкости 0..1, ниже которого звук считается тишиной."""
        return (100 - self.sensitivity) / 100 * GATE_MAX

    def process(self, data):
        """Усиление и шумовой порог для блока звука int16. Заодно обновляет self.level."""
        import numpy as np
        x = np.frombuffer(data, np.int16).astype(np.float32)
        if self.gain != 1.0:
            x = np.clip(x * self.gain, -32768, 32767)
        self.level = min(1.0, float(np.sqrt(np.mean(x * x))) / 32768 * LEVEL_SCALE) if len(x) else 0.0
        if self.level < self.gate_level():
            x[:] = 0
        return x.astype(np.int16).tobytes()

    def run(self):
        try:
            import sounddevice as sd
            import vosk
            vosk.SetLogLevel(-1)
            model = vosk.Model(ascii_model_path(self.model_path))
            rec = vosk.KaldiRecognizer(model, RATE)
        except Exception as e:
            log.exception("Модель распознавания не загрузилась")
            self.on_error(str(e), "model")
            return
        worked = False  # микрофон уже хоть раз открылся
        while True:
            self.switch.clear()
            q = queue.Queue(maxsize=300)

            def callback(indata, frames, t, status, q=q):
                with contextlib.suppress(queue.Full):
                    q.put_nowait(bytes(indata))

            device = resolve_device(self.device_name)
            try:
                stream = sd.RawInputStream(samplerate=RATE, blocksize=4000, dtype="int16", channels=1,
                                           callback=callback, device=device)
            except Exception as e:
                if device is not None:  # выбранный микрофон не открылся — пробуем микрофон по умолчанию
                    log.info("Микрофон %s не открылся (%s), беру по умолчанию", self.device_name, e)
                    self.device_name = None
                    continue
                if worked:  # микрофон уже работал и пропал (сон, гарнитуру выдернули) — ждём, пока вернётся
                    log.info("Микрофон пока не открывается (%s), пробую снова", e)
                    time.sleep(3)
                    _refresh_devices(sd)
                    continue
                log.exception("Ошибка микрофона")
                self.on_error(str(e))
                return
            try:
                self.active_name = sd.query_devices(device if device is not None else sd.default.device[0])["name"]
            except Exception:
                self.active_name = default_input_name()
            rec.Reset()
            worked = True
            try:
                if self._listen(stream, q, rec) == "stale":
                    time.sleep(1)
                    _refresh_devices(sd)  # список устройств мог поменяться — иначе откроем «мёртвый» микрофон
            except Exception as e:
                log.exception("Ошибка микрофона/распознавания")
                self.on_error(str(e))
                return

    def _listen(self, stream, q, rec):
        with stream:
            log.info("Микрофон открыт: %s", self.active_name)
            buf = bytearray()
            was_muted = False
            last_audio = time.time()
            while not self.switch.is_set():
                try:
                    data = self.process(q.get(timeout=0.5))
                    last_audio = time.time()
                except queue.Empty:
                    # звук приходит каждые 0,25 с даже в тишине; если его нет — микрофон отвалился
                    # (сон компьютера, гарнитуру переподключили) — переоткрываем, иначе Капри «оглохнет» молча
                    if time.time() - last_audio > 3:
                        log.info("Микрофон перестал присылать звук — переоткрываю")
                        return "stale"
                    continue
                if self.muted.is_set():
                    was_muted = True
                    continue
                if was_muted or self.reset_req.is_set():
                    was_muted = False
                    self.reset_req.clear()
                    rec.Reset()
                    buf.clear()
                buf += data
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get("text", "").strip()
                    audio = bytes(buf)
                    buf.clear()
                    if text:
                        self.on_final(text, audio)
                else:
                    part = json.loads(rec.PartialResult()).get("partial", "")
                    if part:
                        self.on_partial(part)
                    if len(buf) > RATE * 2 * 25:
                        del buf[:RATE * 2 * 5]
