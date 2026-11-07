"""Ответы на вопросы через локальную модель в llama.cpp (OpenAI-совместимый сервер, напр. 127.0.0.1:8085).

В отличие от Ollama, сервер модели запускается отдельно (Docker/скрипт), поэтому start_server ничего не поднимает —
только проверяет связь. Формат запросов — OpenAI /v1/chat/completions."""
import datetime
import json
import logging
import os
import random
import re
import subprocess
import threading
import urllib.request
from collections.abc import Callable
from typing import Any

from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.llm_text import LlmText
from src.application.assistant.persona import persona

log = logging.getLogger("capri")
NO_WINDOW = 0x08000000
SEARCH_MARK = "ПОИСК"
NO_THINKING = "Сразу дай готовый ответ от лица Капри. Без рассуждений, без анализа вопроса, без «пользователь хочет»."

SYSTEM = f"""{persona.CHARACTER}

{persona.SPEECH_RULES}
Отвечай на любые вопросы о науке, истории, технике, языке, о себе, советы и просьбы рассказать что-то.
Только если вопрос про текущие события (погода сейчас, свежие новости, курсы валют, цены,
результаты недавних матчей), ответь ровно одним словом: {SEARCH_MARK}"""

# вопросы про свежие данные — на них лучше открыть поиск, а не выдумывать
FRESH = re.compile(r"погод|новост|курс (доллар|евро|рубл|валют|биткоин)|сколько стоит|цена|цены|"
                   r"счет матча|кто выиграл|расписани|пробк|сегодня в мире")

CHATTER_TOPICS = [
    "пожалуйся, что тебе скучно", "подразни пользователя за то, что он долго сидит за компьютером",
    "пошути про то, как тесно жить в компьютере", "сделай комплимент с подколкой",
    "пошути про его рабочий стол или файлы", "скажи что-нибудь загадочное и чуть жутковатое",
    "напомни отдохнуть, но в своём стиле", "похвастайся, что ты быстрее его процессора",
    "вспомни о небе и о том, что хочешь собственное тело",
]


class LlamaCppChatModelAdapter(ILocalChatModelAdapter):
    """Локальная модель в llama.cpp. Болтает тем же характером Капри, что и раньше, но через OpenAI-сервер."""

    def __init__(self, settings: dict[str, Any]) -> None:
        base = str(settings.get("local_llm_url") or "http://127.0.0.1:8085").rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        self._url = base + "/chat/completions"
        self._model = settings.get("local_model") or "local"
        self.history: list[dict[str, str]] = []
        # папка со стеком LLM (Docker + прокси и скрипты start-chat-headless.ps1 / stop-chat.ps1).
        # Пусто — управлять сервером нечем, запускается отдельно (как раньше).
        self._dir = str(settings.get("local_llm_dir") or "").strip()
        self._lock = threading.Lock()  # чтобы запуск и остановка не наложились друг на друга

    def start_server(self) -> None:
        """Поднять сервер модели, если он ещё не отвечает (Docker-контейнер + прокси). Блокирует до
        готовности или таймаута — вызывать лучше в отдельном потоке."""
        if self.available:
            return
        script = self._script("start-chat-headless.ps1")
        if not script:
            log.info("llama.cpp: local_llm_dir не задан — сервер модели ожидается на %s отдельно", self._url)
            return
        with self._lock:
            if self.available:
                return
            log.info("Поднимаю локальную модель: %s", script)
            code = self._run_ps(script, timeout=660)
            log.info("Запуск локальной модели: код %s, доступна=%s", code, self.available)

    def stop_server(self) -> None:
        """Остановить контейнер модели — освободить VRAM (напр. на время генерации картинки)."""
        script = self._script("stop-chat.ps1")
        if not script:
            return
        with self._lock:
            log.info("Останавливаю локальную модель, освобождаю VRAM")
            self._run_ps(script, timeout=120)

    def _script(self, name: str) -> str | None:
        if not self._dir:
            return None
        path = os.path.join(self._dir, name)
        return path if os.path.exists(path) else None

    @staticmethod
    def _run_ps(script: str, timeout: int) -> int | None:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
                timeout=timeout, creationflags=NO_WINDOW,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return r.returncode
        except Exception as e:
            log.info("Не удалось выполнить %s: %s", script, e)
            return None

    def set_on_model_change(self, callback: Callable[[str], None]) -> None:
        return  # модель фиксированная, переключать нечего

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self._url.replace("/chat/completions", "/models"), timeout=1.5):
                return True
        except Exception:
            return False

    def _post(self, payload: dict, timeout: int) -> dict:
        req = urllib.request.Request(self._url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _chat(self, messages: list[dict[str, str]], max_tokens: int = 300) -> str:
        resp = self._post({
            "model": self._model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.6,
            "top_p": 0.95,
        }, 120)
        text = LlmText.strip_reasoning(resp["choices"][0]["message"].get("content") or "")
        if LlmText.REASONING.search(text):
            log.info("Модель рассуждает вслух вместо ответа")
            if messages[-1].get("content", "").startswith(NO_THINKING):
                return ""
            return self._chat(messages + [{"role": "system", "content": NO_THINKING}], max_tokens)
        return text

    def instruct(self, system: str, user: str) -> str | None:
        """Разовый ответ на инструкцию без характера и истории (напр. подбор тегов для картинки)."""
        try:
            text = self._chat([{"role": "system", "content": system}, {"role": "user", "content": user}], 200)
        except Exception as e:
            log.info("instruct недоступен: %s", e)
            return None
        text = re.sub(r"\s+", " ", (text or "")).strip()
        return text or None

    def ask(self, question: str) -> str | None:
        """Текст ответа или None, если лучше открыть поиск."""
        if FRESH.search(question.lower()):
            return None
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        self.history.append({"role": "user", "content": question})
        messages = [{"role": "system", "content": SYSTEM + "\n" + persona.user_context() + f"\nСейчас {now}."}] + self.history
        try:
            answer = self._chat(messages)
            if LlmText.FOREIGN.search(answer):  # иногда срывается на другой алфавит — пробуем ещё раз
                answer = self._chat(messages + [{"role": "system", "content":
                                    "Ответь заново, строго только русскими буквами, без иероглифов."}])
            answer = re.sub(r"\s+", " ", LlmText.FOREIGN.sub("", answer)).strip()
        except Exception as e:
            log.info("Локальная модель недоступна: %s", e)
            self.history.pop()
            return None
        recent = [m["content"] for m in self.history if m["role"] == "assistant"]
        answer = LlmText.naturalize(LlmText.drop_repeats(LlmText.drop_third_person(answer), self.history), question, recent)
        answer = re.sub(r"\s*\([^)]*\)", "", answer)                      # ремарки в скобках
        answer = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", answer)  # эмодзи
        answer = re.sub(r"\s+", " ", answer).strip()
        answer = answer[:1].upper() + answer[1:]
        broken = len(answer) < 40 and not re.search(r"[.!?…]$", answer)
        if not answer or broken or SEARCH_MARK in answer.upper()[:20]:
            self.history.pop()
            return None
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def chatter(self) -> str | None:
        """Короткая спонтанная реплика, когда Капри появляется сама. None — если модель недоступна."""
        try:
            text = self._chat([
                {"role": "system", "content": SYSTEM + "\n" + persona.user_context()},
                {"role": "user", "content":
                 "Ты сама решила ненадолго появиться на экране. Скажи одну короткую спонтанную фразу, "
                 f"до пятнадцати слов. Тема: {random.choice(CHATTER_TOPICS)}. "
                 "Не спрашивай, чем помочь, и не упоминай команды."},
            ], max_tokens=60)
        except Exception:
            return None
        text = LlmText.drop_third_person(re.sub(r"\s+", " ", LlmText.FOREIGN.sub("", text)).strip().strip('"«»'))
        text = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", text).strip()
        return text if 5 < len(text) < 160 and re.search(r"[.!?…]$", text) else None

    def summarize_report(self, report: str) -> str | None:
        try:
            return self._chat([
                {"role": "system", "content": SYSTEM + "\n" + persona.user_context()},
                {"role": "user", "content":
                 "Вот отчёт диагностики моего ПК. Скажи 2–4 предложения: общее состояние, главные "
                 "проблемы и что сделать. Безвредные ошибки вроде DistributedCOM не раздувай.\n\n"
                 + report[:12000]},
            ], max_tokens=400) or None
        except Exception:
            return None
