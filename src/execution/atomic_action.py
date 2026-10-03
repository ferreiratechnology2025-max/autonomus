from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from src.core.config import Settings
from src.execution.action_executor import ActionExecutor


@dataclass
class AtomicAction:
    name: str
    execute: Callable[[], Awaitable[bool]] | Callable[[], bool]
    compensate: Optional[Callable[[], Awaitable[bool]] | Callable[[], bool]] = None
    pre_state_hash: Optional[str] = None
    post_state_hash: Optional[str] = None


class AtomicActionContext:
    def __init__(self, perception, executor: ActionExecutor) -> None:
        self.perception = perception
        self.executor = executor
        self.actions: list[AtomicAction] = []
        self.pre_screenshot: Optional[bytes] = None
        self._compensation_enabled = getattr(executor, "_config", Settings()).enable_compensation

    async def __aenter__(self):
        self.pre_screenshot = await self.perception.capture()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self._compensation_enabled:
            await self._do_rollback()
        return False

    async def add_action(self, action: AtomicAction) -> None:
        self.actions.append(action)

    async def commit(self) -> bool:
        executed: list[AtomicAction] = []
        for action in self.actions:
            try:
                result = action.execute()
                if hasattr(result, "__await__"):
                    result = await result
                if not result:
                    logger.error(f"AtomicAction '{action.name}' failed")
                    if self._compensation_enabled:
                        await self._do_rollback(executed)
                    return False
                executed.append(action)
                logger.info(f"AtomicAction '{action.name}' committed")
            except Exception as e:
                logger.error(f"AtomicAction '{action.name}' raised: {e}")
                if self._compensation_enabled:
                    await self._do_rollback(executed)
                return False
        logger.info(f"Atomic transaction committed ({len(executed)} actions)")
        return True

    async def _do_rollback(self, executed: Optional[list[AtomicAction]] = None) -> None:
        targets = executed if executed is not None else list(reversed(self.actions))
        for action in reversed(targets):
            if action.compensate is not None:
                try:
                    result = action.compensate()
                    if hasattr(result, "__await__"):
                        result = await result
                    logger.info(f"Compensation for '{action.name}': {'ok' if result else 'failed'}")
                except Exception as e:
                    logger.error(f"Compensation for '{action.name}' failed: {e}")
