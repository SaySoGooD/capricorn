from typing import Any

from dependency_injector import containers, providers
from PySide6.QtWidgets import QApplication

from src.adapter.code.code_rag_adapter import CodeRagAdapter
from src.adapter.file.json_settings_store import JsonSettingsStore
from src.adapter.image.comfyui_adapter import ComfyUiAdapter
from src.adapter.llm.claude_chat_model_adapter import ClaudeChatModelAdapter
from src.adapter.llm.fastembed_adapter import FastEmbedAdapter
from src.adapter.llm.llama_cpp_chat_model import LlamaCppChatModelAdapter
from src.adapter.qt.avatar_widget import Avatar
from src.adapter.qt.qt_avatar_view import QtAvatarView
from src.adapter.qt.tray_menu import TrayMenu
from src.adapter.speech.google_speech_refiner_adapter import GoogleSpeechRefinerAdapter
from src.adapter.speech.sounddevice_audio_devices_adapter import SoundDeviceAudioDevicesAdapter
from src.adapter.speech.vosk_listener_adapter import VoskListenerFactory
from src.adapter.tts.edge_speaker_adapter import EdgeSpeakerAdapter
from src.adapter.tts.glitch_sound_adapter import GlitchSoundAdapter
from src.adapter.web.cdp_browser_adapter import CdpBrowserAdapter
from src.adapter.web.wikipedia_adapter import WikipediaAdapter
from src.adapter.web.youtube_search_adapter import YouTubeSearchAdapter
from src.adapter.windows.com_thread_setup_adapter import ComThreadSetupAdapter
from src.adapter.windows.telegram_messenger_adapter import TelegramMessengerAdapter
from src.adapter.windows.windows_app_catalog_adapter import WindowsAppCatalogAdapter
from src.adapter.windows.windows_audio_adapter import WindowsAudioAdapter
from src.adapter.windows.windows_browser_adapter import WindowsBrowserAdapter
from src.adapter.windows.windows_diagnostics_adapter import WindowsDiagnosticsAdapter
from src.adapter.windows.windows_display_adapter import WindowsDisplayAdapter
from src.adapter.windows.windows_file_system_adapter import WindowsFileSystemAdapter
from src.adapter.windows.windows_keyboard_adapter import WindowsKeyboardAdapter
from src.adapter.windows.windows_media_session_adapter import WindowsMediaSessionAdapter
from src.adapter.windows.windows_power_adapter import WindowsPowerAdapter
from src.adapter.windows.windows_process_adapter import WindowsProcessAdapter
from src.adapter.windows.windows_screenshot_adapter import WindowsScreenshotAdapter
from src.adapter.windows.windows_ui_automation_adapter import WindowsUiAutomationAdapter
from src.adapter.windows.windows_window_adapter import WindowsWindowAdapter
from src.adapter.windows.windows_youtube_player_adapter import WindowsYouTubePlayerAdapter
from src.application.assistant.command_context import CommandContext
from src.application.assistant.dto.settings_dto import SettingsLoadResultDTO
from src.application.assistant.interfaces.i_app_catalog_adapter import IAppCatalogAdapter
from src.application.assistant.interfaces.i_app_commands_usecase import IAppCommandsUseCase
from src.application.assistant.interfaces.i_assistant_session_usecase import IAssistantSessionUseCase
from src.application.assistant.interfaces.i_audio_devices_adapter import IAudioDevicesAdapter
from src.application.assistant.interfaces.i_avatar_commands_usecase import IAvatarCommandsUseCase
from src.application.assistant.interfaces.i_avatar_view import IAvatarView
from src.application.assistant.interfaces.i_browser_adapter import IBrowserAdapter
from src.application.assistant.interfaces.i_browser_automation_adapter import IBrowserAutomationAdapter
from src.application.assistant.interfaces.i_browser_automation_usecase import IBrowserAutomationUseCase
from src.application.assistant.interfaces.i_chat_model_adapter import IChatModelAdapter
from src.application.assistant.interfaces.i_code_rag_adapter import ICodeRagAdapter
from src.application.assistant.interfaces.i_diagnostics_adapter import IDiagnosticsAdapter
from src.application.assistant.interfaces.i_display_adapter import IDisplayAdapter
from src.application.assistant.interfaces.i_embedding_adapter import IEmbeddingAdapter
from src.application.assistant.interfaces.i_encyclopedia_adapter import IEncyclopediaAdapter
from src.application.assistant.interfaces.i_file_system_adapter import IFileSystemAdapter
from src.application.assistant.interfaces.i_handle_command_usecase import IHandleCommandUseCase
from src.application.assistant.interfaces.i_image_generation_adapter import IImageGenerationAdapter
from src.application.assistant.interfaces.i_image_generation_usecase import IImageGenerationUseCase
from src.application.assistant.interfaces.i_input_commands_usecase import IInputCommandsUseCase
from src.application.assistant.interfaces.i_keyboard_adapter import IKeyboardAdapter
from src.application.assistant.interfaces.i_listener_factory import IListenerFactory
from src.application.assistant.interfaces.i_local_chat_model_adapter import ILocalChatModelAdapter
from src.application.assistant.interfaces.i_media_commands_usecase import IMediaCommandsUseCase
from src.application.assistant.interfaces.i_media_session_adapter import IMediaSessionAdapter
from src.application.assistant.interfaces.i_memory_commands_usecase import IMemoryCommandsUseCase
from src.application.assistant.interfaces.i_messenger_adapter import IMessengerAdapter
from src.application.assistant.interfaces.i_messenger_commands_usecase import IMessengerCommandsUseCase
from src.application.assistant.interfaces.i_open_url_usecase import IOpenUrlUseCase
from src.application.assistant.interfaces.i_power_adapter import IPowerAdapter
from src.application.assistant.interfaces.i_process_adapter import IProcessAdapter
from src.application.assistant.interfaces.i_remember_entry_usecase import IRememberEntryUseCase
from src.application.assistant.interfaces.i_run_chain_usecase import IRunChainUseCase
from src.application.assistant.interfaces.i_screenshot_adapter import IScreenshotAdapter
from src.application.assistant.interfaces.i_self_knowledge_usecase import ISelfKnowledgeUseCase
from src.application.assistant.interfaces.i_settings_store import ISettingsStore
from src.application.assistant.interfaces.i_sound_effects_adapter import ISoundEffectsAdapter
from src.application.assistant.interfaces.i_speaker_adapter import ISpeakerAdapter
from src.application.assistant.interfaces.i_speech_refiner_adapter import ISpeechRefinerAdapter
from src.application.assistant.interfaces.i_system_audio_adapter import ISystemAudioAdapter
from src.application.assistant.interfaces.i_system_commands_usecase import ISystemCommandsUseCase
from src.application.assistant.interfaces.i_thread_setup_adapter import IThreadSetupAdapter
from src.application.assistant.interfaces.i_ui_automation_adapter import IUiAutomationAdapter
from src.application.assistant.interfaces.i_web_commands_usecase import IWebCommandsUseCase
from src.application.assistant.interfaces.i_window_adapter import IWindowAdapter
from src.application.assistant.interfaces.i_youtube_player_adapter import IYouTubePlayerAdapter
from src.application.assistant.interfaces.i_youtube_search_adapter import IYouTubeSearchAdapter
from src.application.assistant.usecases.app_commands_usecase import AppCommandsUseCase
from src.application.assistant.usecases.assistant_session_usecase import AssistantSessionUseCase
from src.application.assistant.usecases.avatar_commands_usecase import AvatarCommandsUseCase
from src.application.assistant.usecases.browser_automation_usecase import BrowserAutomationUseCase
from src.application.assistant.usecases.handle_command_usecase import HandleCommandUseCase
from src.application.assistant.usecases.image_generation_usecase import ImageGenerationUseCase
from src.application.assistant.usecases.input_commands_usecase import InputCommandsUseCase
from src.application.assistant.usecases.media_commands_usecase import MediaCommandsUseCase
from src.application.assistant.usecases.memory_commands_usecase import MemoryCommandsUseCase
from src.application.assistant.usecases.messenger_commands_usecase import MessengerCommandsUseCase
from src.application.assistant.usecases.open_url_usecase import OpenUrlUseCase
from src.application.assistant.usecases.remember_entry_usecase import RememberEntryUseCase
from src.application.assistant.usecases.run_chain_usecase import RunChainUseCase
from src.application.assistant.usecases.self_knowledge_usecase import SelfKnowledgeUseCase
from src.application.assistant.usecases.system_commands_usecase import SystemCommandsUseCase
from src.application.assistant.usecases.web_commands_usecase import WebCommandsUseCase
from src.main.config import Config


def _load_settings(store: ISettingsStore) -> SettingsLoadResultDTO:
    return store.load()


def _local_chat_model(settings: dict[str, Any]) -> ILocalChatModelAdapter | None:
    """Локальная нейросеть (llama.cpp на 127.0.0.1:8085) включается настройкой local_ai."""
    return LlamaCppChatModelAdapter(settings) if settings.get("local_ai") else None


def _avatar(assets_dir: str, settings: dict[str, Any]) -> Avatar:
    avatar = Avatar(assets_dir)
    avatar.hide_after = float(settings["hide_after_seconds"])
    return avatar


class Container(containers.DeclarativeContainer):
    config: providers.Singleton[Config] = providers.Singleton(Config)

    # ----- настройки пользователя (config.json) -----
    settings_store: providers.Singleton[ISettingsStore] = providers.Singleton(
        JsonSettingsStore,
        path=config.provided.SETTINGS_FILE,
    )
    settings_load: providers.Singleton[SettingsLoadResultDTO] = providers.Singleton(
        _load_settings,
        store=settings_store,
    )
    settings = settings_load.provided.settings
    command_context: providers.Singleton[CommandContext] = providers.Singleton(
        CommandContext,
        settings=settings,
    )

    # ----- Windows -----
    window_adapter: providers.Singleton[IWindowAdapter] = providers.Singleton(WindowsWindowAdapter)
    keyboard_adapter: providers.Singleton[IKeyboardAdapter] = providers.Singleton(WindowsKeyboardAdapter)
    browser_adapter: providers.Singleton[IBrowserAdapter] = providers.Singleton(WindowsBrowserAdapter)
    youtube_player_adapter: providers.Singleton[IYouTubePlayerAdapter] = providers.Singleton(
        WindowsYouTubePlayerAdapter,
    )
    app_catalog_adapter: providers.Singleton[IAppCatalogAdapter] = providers.Singleton(WindowsAppCatalogAdapter)
    system_audio_adapter: providers.Singleton[ISystemAudioAdapter] = providers.Singleton(WindowsAudioAdapter)
    display_adapter: providers.Singleton[IDisplayAdapter] = providers.Singleton(WindowsDisplayAdapter)
    power_adapter: providers.Singleton[IPowerAdapter] = providers.Singleton(WindowsPowerAdapter)
    media_session_adapter: providers.Singleton[IMediaSessionAdapter] = providers.Singleton(
        WindowsMediaSessionAdapter,
    )
    process_adapter: providers.Singleton[IProcessAdapter] = providers.Singleton(WindowsProcessAdapter)
    file_system_adapter: providers.Singleton[IFileSystemAdapter] = providers.Singleton(
        WindowsFileSystemAdapter,
        reports_dir=config.provided.REPORTS_DIR,
    )
    diagnostics_adapter: providers.Singleton[IDiagnosticsAdapter] = providers.Singleton(WindowsDiagnosticsAdapter)
    screenshot_adapter: providers.Singleton[IScreenshotAdapter] = providers.Singleton(
        WindowsScreenshotAdapter,
        folder=config.provided.SCREENSHOTS_DIR,
    )
    messenger_adapter: providers.Singleton[IMessengerAdapter] = providers.Singleton(TelegramMessengerAdapter)
    browser_automation_adapter: providers.Singleton[IBrowserAutomationAdapter] = providers.Singleton(
        CdpBrowserAdapter,
        settings=settings,
        base_dir=config.provided.BASE_DIR,
    )
    thread_setup_adapter: providers.Singleton[IThreadSetupAdapter] = providers.Singleton(ComThreadSetupAdapter)
    ui_automation_adapter: providers.Singleton[IUiAutomationAdapter] = providers.Singleton(WindowsUiAutomationAdapter)
    image_generation_adapter: providers.Singleton[IImageGenerationAdapter] = providers.Singleton(
        ComfyUiAdapter,
        settings=settings,
        folder=config.provided.SCREENSHOTS_DIR,
    )

    # ----- интернет -----
    youtube_search_adapter: providers.Singleton[IYouTubeSearchAdapter] = providers.Singleton(YouTubeSearchAdapter)
    encyclopedia_adapter: providers.Singleton[IEncyclopediaAdapter] = providers.Singleton(WikipediaAdapter)

    # ----- речь и нейросети -----
    speaker_adapter: providers.Singleton[ISpeakerAdapter] = providers.Singleton(
        EdgeSpeakerAdapter,
        settings=settings,
    )
    listener_factory: providers.Singleton[IListenerFactory] = providers.Singleton(
        VoskListenerFactory,
        base_dir=config.provided.BASE_DIR,
        settings=settings,
    )
    audio_devices_adapter: providers.Singleton[IAudioDevicesAdapter] = providers.Singleton(
        SoundDeviceAudioDevicesAdapter,
    )
    speech_refiner_adapter: providers.Singleton[ISpeechRefinerAdapter] = providers.Singleton(
        GoogleSpeechRefinerAdapter,
    )
    sound_effects_adapter: providers.Singleton[ISoundEffectsAdapter] = providers.Singleton(GlitchSoundAdapter)
    cloud_chat_adapter: providers.Singleton[IChatModelAdapter] = providers.Singleton(
        ClaudeChatModelAdapter,
        settings=settings,
    )
    local_chat_adapter: providers.Singleton[ILocalChatModelAdapter | None] = providers.Singleton(
        _local_chat_model,
        settings=settings,
    )
    # ----- RAG по собственному коду (эмбеддинги на CPU, чтобы не трогать VRAM) -----
    embedding_adapter: providers.Singleton[IEmbeddingAdapter] = providers.Singleton(
        FastEmbedAdapter,
        settings=settings,
    )
    code_rag_adapter: providers.Singleton[ICodeRagAdapter] = providers.Singleton(
        CodeRagAdapter,
        embedding=embedding_adapter,
        base_dir=config.provided.BASE_DIR,
        settings=settings,
    )

    # ----- use case'ы команд -----
    open_url_usecase: providers.Factory[IOpenUrlUseCase] = providers.Factory(
        OpenUrlUseCase,
        context=command_context,
        browser=browser_adapter,
    )
    remember_entry_usecase: providers.Factory[IRememberEntryUseCase] = providers.Factory(
        RememberEntryUseCase,
        context=command_context,
        store=settings_store,
    )
    avatar_commands_usecase: providers.Factory[IAvatarCommandsUseCase] = providers.Factory(AvatarCommandsUseCase)
    memory_commands_usecase: providers.Factory[IMemoryCommandsUseCase] = providers.Factory(
        MemoryCommandsUseCase,
        context=command_context,
        remember=remember_entry_usecase,
        browser=browser_adapter,
        window=window_adapter,
        open_url=open_url_usecase,
    )
    system_commands_usecase: providers.Factory[ISystemCommandsUseCase] = providers.Factory(
        SystemCommandsUseCase,
        context=command_context,
        power=power_adapter,
        audio=system_audio_adapter,
        display=display_adapter,
        diagnostics=diagnostics_adapter,
        file_system=file_system_adapter,
        screenshot=screenshot_adapter,
        processes=process_adapter,
        cloud_chat=cloud_chat_adapter,
        local_chat=local_chat_adapter,
    )
    input_commands_usecase: providers.Factory[IInputCommandsUseCase] = providers.Factory(
        InputCommandsUseCase,
        context=command_context,
        keyboard=keyboard_adapter,
        window=window_adapter,
        youtube=youtube_player_adapter,
        browser=browser_adapter,
        ui_automation=ui_automation_adapter,
    )
    media_commands_usecase: providers.Factory[IMediaCommandsUseCase] = providers.Factory(
        MediaCommandsUseCase,
        context=command_context,
        media=media_session_adapter,
        youtube=youtube_player_adapter,
    )
    messenger_commands_usecase: providers.Factory[IMessengerCommandsUseCase] = providers.Factory(
        MessengerCommandsUseCase,
        window=window_adapter,
        catalog=app_catalog_adapter,
        messenger=messenger_adapter,
    )
    app_commands_usecase: providers.Factory[IAppCommandsUseCase] = providers.Factory(
        AppCommandsUseCase,
        context=command_context,
        catalog=app_catalog_adapter,
        file_system=file_system_adapter,
        processes=process_adapter,
        window=window_adapter,
        open_url=open_url_usecase,
    )
    web_commands_usecase: providers.Factory[IWebCommandsUseCase] = providers.Factory(
        WebCommandsUseCase,
        context=command_context,
        open_url=open_url_usecase,
        youtube_search=youtube_search_adapter,
        youtube=youtube_player_adapter,
        encyclopedia=encyclopedia_adapter,
    )
    image_generation_usecase: providers.Factory[IImageGenerationUseCase] = providers.Factory(
        ImageGenerationUseCase,
        context=command_context,
        image=image_generation_adapter,
        file_system=file_system_adapter,
        local_chat=local_chat_adapter,
    )
    browser_automation_usecase: providers.Factory[IBrowserAutomationUseCase] = providers.Factory(
        BrowserAutomationUseCase,
        context=command_context,
        browser=browser_automation_adapter,
        local_chat=local_chat_adapter,
    )
    self_knowledge_usecase: providers.Factory[ISelfKnowledgeUseCase] = providers.Factory(
        SelfKnowledgeUseCase,
        context=command_context,
        rag=code_rag_adapter,
        local_chat=local_chat_adapter,
    )
    run_chain_usecase: providers.Factory[IRunChainUseCase] = providers.Factory(
        RunChainUseCase,
        context=command_context,
        keyboard=keyboard_adapter,
        window=window_adapter,
        youtube=youtube_player_adapter,
        messenger=messenger_adapter,
    )
    handle_command_usecase: providers.Singleton[IHandleCommandUseCase] = providers.Singleton(
        HandleCommandUseCase,
        context=command_context,
        browser=browser_adapter,
        youtube=youtube_player_adapter,
        run_chain=run_chain_usecase,
        avatar=avatar_commands_usecase,
        memory=memory_commands_usecase,
        system=system_commands_usecase,
        input=input_commands_usecase,
        media=media_commands_usecase,
        messenger=messenger_commands_usecase,
        apps=app_commands_usecase,
        web=web_commands_usecase,
        image=image_generation_usecase,
        self_knowledge=self_knowledge_usecase,
        browser_auto=browser_automation_usecase,
    )

    # ----- интерфейс (Qt): QApplication создаётся в main и подставляется через override -----
    qt_app: providers.Dependency[QApplication] = providers.Dependency(instance_of=QApplication)
    avatar_widget: providers.Singleton[Avatar] = providers.Singleton(
        _avatar,
        assets_dir=config.provided.ASSETS_DIR,
        settings=settings,
    )
    avatar_view: providers.Singleton[IAvatarView] = providers.Singleton(
        QtAvatarView,
        avatar=avatar_widget,
        app=qt_app,
    )

    # ----- сессия ассистента -----
    assistant_session_usecase: providers.Singleton[IAssistantSessionUseCase] = providers.Singleton(
        AssistantSessionUseCase,
        settings=settings,
        settings_error=settings_load.provided.error,
        store=settings_store,
        context=command_context,
        handle_command=handle_command_usecase,
        cloud_chat=cloud_chat_adapter,
        local_chat=local_chat_adapter,
        speaker=speaker_adapter,
        listener_factory=listener_factory,
        audio_devices=audio_devices_adapter,
        speech_refiner=speech_refiner_adapter,
        sound_effects=sound_effects_adapter,
        view=avatar_view,
        window=window_adapter,
        catalog=app_catalog_adapter,
        thread_setup=thread_setup_adapter,
        self_knowledge=self_knowledge_usecase,
    )
    tray_menu: providers.Singleton[TrayMenu] = providers.Singleton(
        TrayMenu,
        app=qt_app,
        avatar=avatar_widget,
        session=assistant_session_usecase,
        context=command_context,
        remember=remember_entry_usecase,
        open_url=open_url_usecase,
        settings_path=config.provided.SETTINGS_FILE,
    )


container = Container()
