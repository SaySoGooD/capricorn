from src.adapter.zapret import zapret_lists
from src.application.assistant.interfaces.i_zapret_adapter import IZapretAdapter


class ZapretAdapter(IZapretAdapter):
    def is_network_error(self, error: str) -> bool:
        return bool(zapret_lists.NETWORK_ERROR.search(error))

    def running(self) -> bool:
        return zapret_lists.running()

    def find_all_lists(self) -> list[str]:
        return zapret_lists.find_all_lists()

    def excluded(self, lists: str) -> bool:
        return zapret_lists.excluded(lists)

    def add_exclude(self, lists: str) -> str:
        return zapret_lists.add_exclude(lists)
