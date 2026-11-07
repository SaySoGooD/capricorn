from src.adapter.windows import ui_automation
from src.application.assistant.interfaces.i_ui_automation_adapter import IUiAutomationAdapter


class WindowsUiAutomationAdapter(IUiAutomationAdapter):
    def click_element(self, name: str, hwnd: int | None = None) -> bool:
        return ui_automation.click(name, hwnd)
