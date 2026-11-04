"""Настройки по умолчанию. config.json дополняет и переопределяет их."""


DEFAULTS = {
    "enable_ai": False,
    "local_ai": True,
    "local_model": "qwen3:8b",
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
