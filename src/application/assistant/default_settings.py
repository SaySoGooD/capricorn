"""Настройки по умолчанию. config.json дополняет и переопределяет их."""
from typing import Any

DEFAULTS: dict[str, Any] = {
    "enable_ai": False,
    "local_ai": True,
    "local_model": "qwen3:8b",
    "local_llm_dir": r"D:\ai-test\llm",  # папка стека LLM (Docker+прокси, скрипты start-chat-headless.ps1/stop-chat.ps1);
                                         # "" — Капри не управляет сервером модели, он запускается отдельно
    "pause_llm_on_draw": True, # на время рисования выгружать LLM из VRAM (35B и SDXL вместе не влезают в 16 ГБ)
    "stop_ai_on_exit": True,   # при выходе из Капри гасить и ComfyUI, и локальную модель
    "self_rag": True,          # Капри отвечает о себе по своему коду (RAG): «что у тебя под капотом», «как работает …»
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # эмбеддинги (CPU/ONNX), качается один раз
    "rag_top_k": 8,            # сколько кусков кода подкладывать модели для ответа о себе
    "browser_cdp": True,       # свой браузер Капри по CDP: «запусти свой браузер», «открой … в своём браузере»
    "browser_cdp_port": 9222,  # порт отладки её браузера (отдельный от твоего Chrome)
    "browser_exe": "",         # путь к chrome.exe/msedge.exe; "" — ищется в стандартных местах
    "browser_profile_dir": "", # профиль её браузера; "" — %LOCALAPPDATA%\Capri\browser (чистый, свой)
    "image_ai": True,          # генерация картинок через локальный ComfyUI («нарисуй …»)
    "comfyui_url": "http://127.0.0.1:8188",
    "comfyui_dir": r"D:\ai-test\ComfyUI",  # папка ComfyUI — Капри сама поднимет/погасит его («запусти/выгрузи ComfyUI»);
                                           # "" — не управлять, сервер запускается вручную
    "comfyui_python": "",      # python ComfyUI; "" — берётся <comfyui_dir>\.venv\Scripts\python.exe
    "comfyui_llm_tags": True,  # перед рисованием локальная модель подбирает booru-теги по описанию
    "comfyui_model": "ponyDiffusionV6XL.safetensors",  # чекпойнт в ComfyUI/models/checkpoints
    "comfyui_steps": 25,
    "comfyui_cfg": 7.0,
    "comfyui_size": 1024,      # SDXL рисует в 1024; для SD1.5 поставь 512
    "comfyui_sampler": "euler",
    "comfyui_scheduler": "normal",
    "comfyui_prompt_prefix": "score_9, score_8_up, score_7_up, ",  # Pony любит score-теги; для иных моделей очисти
    "comfyui_negative": "score_6, score_5, score_4, worst quality, low quality, blurry, watermark, text, signature",
    "barge_in": True,
    "mic_device": None,
    "chatter": True,
    "chatter_min_minutes": 15,
    "chatter_max_minutes": 40,
    "roam_chance": 0.5,
    "teleport_on_answer": True,
    "search_when_unsure": True,
    "voice_volume": 100,     # громкость голоса Капри 0..100 (общая громкость Windows не меняется)
    "mic_gain": 1.0,         # громкость микрофона для Капри: 1 — как есть, 2 — вдвое громче
    "mic_sensitivity": 100,  # 100 — слышит всё; меньше — тихий шум и фон отбрасываются
    "user_name_mode": "none",  # как называть пользователя: "custom" — user_name, "windows" — имя пользователя
                               # Windows, "pc" — имя компьютера, "none" — не называть
    "user_name": "",
    "user_gender": "male",     # "male" / "female" — в каком роде Капри к тебе обращается
    "browser": "",
    "replies": {},           # свои ответы: {"фраза": "что ответит Капри"} — проверяются раньше команд и нейросети  # в каком браузере открывать сайты: "хром", "яндекс", "опера"… или путь к exe; "" — как в Windows
    "anthropic_api_key": "",
    "model": "claude-opus-5-5",
    "wake_words": ["капри", "каприз", "капре", "кепри", "капли"],
    "use_google_stt": True,
    "voice": "ru-RU-SvetlanaNeural",
    "tts_engine": "edge",
    "voice_rate": "+10%",
    "voice_pitch": "+15Hz",
    "voice_shift": 0,
    "voice_lively": False,
    "voice_fx": 1.8,
    "listen_window_seconds": 8,
    "followup_seconds": 6,
    "hide_after_seconds": 12,
    "greet_on_start": True,
    "vosk_model": "models/vosk-model-small-ru-0.22",
    "sites": {
        "ютуб": "https://www.youtube.com", "youtube": "https://www.youtube.com",
        "гугл": "https://www.google.com", "google": "https://www.google.com",
        "яндекс": "https://ya.ru", "вк": "https://vk.com", "вконтакте": "https://vk.com",
        "почту": "https://mail.google.com", "почта": "https://mail.google.com",
        "гитхаб": "https://github.com", "твич": "https://www.twitch.tv",
        "википедию": "https://ru.wikipedia.org", "википедия": "https://ru.wikipedia.org",
        "переводчик": "https://translate.google.com", "карты": "https://yandex.ru/maps",
        "погоду": "https://yandex.ru/pogoda", "chatgpt": "https://chatgpt.com",
        "клод": "https://claude.ai", "кинопоиск": "https://www.kinopoisk.ru",
        "авито": "https://www.avito.ru", "озон": "https://www.ozon.ru",
        "вайлдберриз": "https://www.wildberries.ru"
    },
    "apps": {
        "блокнот": "notepad", "калькулятор": "calc", "проводник": "explorer",
        "диспетчер задач": "taskmgr", "параметры": "ms-settings:", "настройки": "ms-settings:",
        "панель управления": "control", "командную строку": "cmd", "командная строка": "cmd",
        "терминал": "wt", "пейнт": "mspaint", "paint": "mspaint", "ворд": "winword",
        "эксель": "excel", "браузер": "https://www.google.com",
        "настройки звука": "ms-settings:sound", "настройки экрана": "ms-settings:display",
        "корзину": "shell:RecycleBinFolder", "загрузки": "shell:Downloads"
    },
    "app_aliases": {
        "хром": "chrome", "гугл хром": "google chrome", "стим": "steam", "дискорд": "discord",
        "телеграм": "telegram", "телеграмм": "telegram", "спотифай": "spotify",
        "опера": "opera", "яндекс браузер": "yandex", "вс код": "visual studio code",
        "визуал студио код": "visual studio code", "обс": "obs", "эпик геймс": "epic games",
        "ватсап": "whatsapp", "зум": "zoom", "фотошоп": "photoshop", "майнкрафт": "minecraft"
    }
}
