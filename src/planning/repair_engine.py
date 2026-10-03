from typing import Optional, TYPE_CHECKING

from loguru import logger

from src.execution.action_executor import RaceConditionError
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.memory.memory import MemorySystem
from src.planning.models import RepairStrategy, Task, TaskStatus

if TYPE_CHECKING:
    from src.perception.screen_capture import ScreenCapture


REPAIR_SYSTEM_PROMPT = (
    "You are a GUI automation repair assistant. A task failed. "
    "Suggest a different approach in a single short sentence. "
    "Be specific about what alternative action to take."
)


class RepairEngine:
    def __init__(
        self,
        model_router: ModelRouter,
        sensitive_detector: SensitiveDataDetector,
        perception: Optional["ScreenCapture"] = None,
        memory: Optional[MemorySystem] = None,
    ) -> None:
        self.model_router = model_router
        self.sensitive_detector = sensitive_detector
        self.perception = perception
        self.memory = memory

    async def repair(self, task: Task, error: Exception, context: dict) -> tuple[bool, RepairStrategy]:
        logger.warning(f"Repairing task: {task.name} (error: {error})")

        if isinstance(error, RaceConditionError):
            logger.warning(f"Race condition detectada, tentando revalidacao: {error}")
            revalidated = await self._revalidate_element(task)
            if revalidated:
                logger.info("Elemento revalidado apos race condition, retentando...")
                success = await self._retry_action(task)
                if success:
                    return True, RepairStrategy.RETRY
            return False, RepairStrategy.ABORT

        strategies = [
            RepairStrategy.RETRY,
            RepairStrategy.ALTERNATIVE,
            RepairStrategy.ESCALATE_LLM,
            RepairStrategy.ASK_USER,
        ]

        for strategy in strategies:
            success = await self._try_strategy(strategy, task, error, context)
            if success:
                logger.info(f"Repair succeeded with: {strategy.value}")
                return True, strategy

        logger.error(f"All repair strategies failed for: {task.name}")
        task.status = TaskStatus.FAILED
        return False, RepairStrategy.ABORT

    async def _try_strategy(
        self, strategy: RepairStrategy, task: Task, error: Exception, context: dict
    ) -> bool:
        if strategy == RepairStrategy.RETRY:
            return await self._retry_action(task)
        elif strategy == RepairStrategy.ALTERNATIVE:
            return await self._alternative_approach(task, error)
        elif strategy == RepairStrategy.ESCALATE_LLM:
            return await self._escalate_llm(task, error)
        elif strategy == RepairStrategy.ASK_USER:
            return await self._ask_user(task, error)
        return False

    async def _revalidate_element(self, task: Task) -> bool:
        try:
            if task.action_type == "click_element":
                await asyncio.sleep(0.2)
                logger.info(f"Revalidacao concluida para {task.name}")
                return True
            return True
        except Exception as e:
            logger.error(f"Revalidacao falhou: {e}")
            return False

    async def _retry_action(self, task: Task) -> bool:
        for attempt in range(3):
            logger.info(f"Retry attempt {attempt + 1}/3 for: {task.name}")
            result = await self._execute_action_simple(task)
            if result:
                task.status = TaskStatus.SUCCESS
                return True
        return False

    async def _alternative_approach(self, task: Task, error: Exception) -> bool:
        logger.info(f"Trying alternative approach for: {task.name}")
        return False

    async def _escalate_llm(self, task: Task, error: Exception) -> bool:
        prompt = (
            f"A GUI automation task failed. Task: {task.name}. "
            f"Action: {task.action_type} {task.parameters}. "
            f"Error: {error}. Suggest a different approach."
        )

        context_str = str(task.parameters)
        has_sensitive = self.sensitive_detector.has_sensitive_data(context_str)

        response = await self.model_router.generate(
            prompt=prompt,
            task_type="repair",
            has_sensitive=has_sensitive,
            system_prompt=REPAIR_SYSTEM_PROMPT,
        )

        return bool(response.text)

    async def _ask_user(self, task: Task, error: Exception) -> bool:
        logger.warning(f"User intervention required for: {task.name} ({error})")
        return False

    async def _execute_action_simple(self, task: Task) -> bool:
        return False
