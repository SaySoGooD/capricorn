from src.application.assistant.interfaces.i_thread_setup_adapter import IThreadSetupAdapter


class ComThreadSetupAdapter(IThreadSetupAdapter):
    def prepare_worker_thread(self) -> None:
        """pycaw и UI Automation требуют COM в потоке, из которого их вызывают."""
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
