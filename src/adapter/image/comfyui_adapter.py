"""Генерация картинок через локальный ComfyUI по его HTTP-API.

ComfyUI рисует по графу нод (workflow). Здесь собирается стандартный SDXL-граф (чекпойнт → два промпта →
пустой латент → KSampler → VAEDecode → SaveImage), ставится в очередь через POST /prompt, затем Капри ждёт
результат в /history и скачивает картинку из /view. Сервер ComfyUI запускается отдельно — как и llama.cpp."""
import datetime
import json
import logging
import os
import random
import subprocess
import time
import urllib.parse
import urllib.request
from typing import Any

from src.application.assistant.interfaces.i_image_generation_adapter import IImageGenerationAdapter

log = logging.getLogger("capri")
NO_WINDOW = 0x08000000       # CREATE_NO_WINDOW — без консольного окна
DETACHED = 0x00000008        # DETACHED_PROCESS — процесс переживает родителя


class ComfyUiAdapter(IImageGenerationAdapter):
    """Рисует картинку локальным ComfyUI. Параметры (адрес, модель, размер, шаги) — из настроек."""

    def __init__(self, settings: dict[str, Any], folder: str) -> None:
        self._settings = settings
        self._folder = folder

    @property
    def _base(self) -> str:
        return str(self._settings.get("comfyui_url") or "http://127.0.0.1:8188").rstrip("/")

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self._base + "/system_stats", timeout=2):
                return True
        except Exception:
            return False

    @property
    def _port(self) -> int:
        try:
            return urllib.parse.urlparse(self._base).port or 8188
        except Exception:
            return 8188

    def start(self, timeout: float = 90.0) -> bool:
        """Поднять сервер ComfyUI, если он не отвечает. Возвращает True, когда сервер готов."""
        if self.available:
            return True
        d = str(self._settings.get("comfyui_dir") or "").strip()
        if not d or not os.path.isdir(d):
            log.info("ComfyUI: comfyui_dir не задан/не найден — запускать нечем (%s)", d)
            return False
        py = str(self._settings.get("comfyui_python") or "").strip()
        if not py or not os.path.exists(py):
            py = os.path.join(d, ".venv", "Scripts", "python.exe")
        if not os.path.exists(py):
            py = "python"
        try:
            proc = subprocess.Popen(
                [py, "-s", "main.py", "--disable-auto-launch", "--port", str(self._port)],
                cwd=d, creationflags=NO_WINDOW | DETACHED,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            log.exception("ComfyUI: не удалось запустить")
            return False
        try:
            with open(os.path.join(d, "comfyui.pid"), "w") as f:
                f.write(str(proc.pid))
        except Exception:
            pass
        log.info("ComfyUI запускается (pid %s), жду готовности…", proc.pid)
        end = time.time() + timeout
        while time.time() < end:
            if self.available:
                log.info("ComfyUI готов на %s", self._base)
                return True
            time.sleep(1.5)
        log.info("ComfyUI не ответил за %s с после запуска", timeout)
        return False

    def stop(self) -> None:
        """Остановить сервер ComfyUI — освободить видеопамять целиком."""
        d = str(self._settings.get("comfyui_dir") or "").strip()
        pidfile = os.path.join(d, "comfyui.pid") if d else ""
        if pidfile and os.path.exists(pidfile):
            try:
                pid = int(open(pidfile).read().strip())
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], creationflags=NO_WINDOW,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                log.info("ComfyUI: taskkill по pid не вышел: %s", e)
            try:
                os.remove(pidfile)
            except Exception:
                pass
        # подстраховка: прибить любой python, запущенный из папки ComfyUI с main.py
        ps = ("Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
              "Where-Object { $_.Path -like '*ComfyUI*' -and $_.CommandLine -like '*main.py*' } | "
              "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=30, creationflags=NO_WINDOW,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.info("ComfyUI: подстраховочная остановка не вышла: %s", e)
        log.info("ComfyUI остановлен")

    def free_vram(self) -> None:
        """Просим ComfyUI выгрузить модели из VRAM (его эндпоинт /free) — чтобы память вернулась LLM."""
        try:
            self._post_json("/free", {"unload_models": True, "free_memory": True}, timeout=15)
            log.info("ComfyUI освободил видеопамять")
        except Exception as e:
            log.info("ComfyUI /free не сработал: %s", e)

    def _workflow(self, prompt: str, positive: str | None = None) -> dict[str, Any]:
        s = self._settings
        # positive задан — используем его как есть (теги уже подобраны); иначе префикс + описание
        positive = positive if positive is not None else str(s.get("comfyui_prompt_prefix", "")) + prompt
        negative = str(s.get("comfyui_negative", ""))
        size = int(s.get("comfyui_size", 1024))
        return {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": random.randint(0, 2**63 - 1), "steps": int(s.get("comfyui_steps", 25)),
                "cfg": float(s.get("comfyui_cfg", 7.0)), "sampler_name": str(s.get("comfyui_sampler", "euler")),
                "scheduler": str(s.get("comfyui_scheduler", "normal")), "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": str(s.get("comfyui_model", "ponyDiffusionV6XL.safetensors"))}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": size, "height": size, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "capri", "images": ["8", 0]}},
        }

    def _post_json(self, path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        req = urllib.request.Request(self._base + path, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _get_json(self, path: str, timeout: int) -> dict[str, Any]:
        with urllib.request.urlopen(self._base + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _wait_image(self, prompt_id: str, timeout: float = 180.0) -> dict[str, str] | None:
        """Ждём, пока ComfyUI досчитает, и возвращаем описание первой готовой картинки (filename/subfolder/type)."""
        import time
        end = time.time() + timeout
        while time.time() < end:
            try:
                history = self._get_json(f"/history/{prompt_id}", timeout=10)
            except Exception:
                history = {}
            entry = history.get(prompt_id)
            if entry:
                for node in entry.get("outputs", {}).values():
                    images = node.get("images")
                    if images:
                        return images[0]
                return None  # досчитал, но картинок нет (ошибка графа)
            time.sleep(1.5)
        log.info("ComfyUI не ответил картинкой за %s с", timeout)
        return None

    def generate(self, prompt: str, positive: str | None = None) -> str | None:
        prompt = (prompt or "").strip()
        if not prompt:
            return None
        import uuid
        client_id = uuid.uuid4().hex
        try:
            resp = self._post_json("/prompt", {"prompt": self._workflow(prompt, positive),
                                               "client_id": client_id}, timeout=15)
        except Exception:
            log.exception("ComfyUI: не удалось поставить задачу")
            return None
        if resp.get("node_errors"):
            log.error("ComfyUI вернул ошибки графа: %s", resp["node_errors"])
            return None
        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            log.error("ComfyUI не вернул prompt_id: %s", resp)
            return None
        image = self._wait_image(prompt_id)
        if not image:
            return None
        query = urllib.parse.urlencode({"filename": image.get("filename", ""),
                                        "subfolder": image.get("subfolder", ""),
                                        "type": image.get("type", "output")})
        try:
            with urllib.request.urlopen(self._base + "/view?" + query, timeout=30) as r:
                data = r.read()
        except Exception:
            log.exception("ComfyUI: не удалось скачать готовую картинку")
            return None
        os.makedirs(self._folder, exist_ok=True)
        path = os.path.join(self._folder, f"art_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
        with open(path, "wb") as f:
            f.write(data)
        log.info("ComfyUI нарисовал: %s", path)
        return path
