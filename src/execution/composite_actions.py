from loguru import logger

from src.execution.action_executor import ActionExecutor


class CompositeActions:
    def __init__(self, executor: ActionExecutor) -> None:
        self.executor = executor

    async def select_all_and_copy(self) -> bool:
        ok1 = await self.executor.press_hotkey("ctrl", "a")
        ok2 = await self.executor.press_hotkey("ctrl", "c")
        success = ok1 and ok2
        logger.info(f"select_all_and_copy: {'success' if success else 'failed'}")
        return success

    async def paste(self) -> bool:
        return await self.executor.press_hotkey("ctrl", "v")

    async def press_enter(self) -> bool:
        return await self.executor.press_hotkey("enter")

    async def press_tab(self, times: int = 1) -> bool:
        for _ in range(times):
            ok = await self.executor.press_hotkey("tab")
            if not ok:
                return False
        return True

    async def press_escape(self) -> bool:
        return await self.executor.press_hotkey("esc")
