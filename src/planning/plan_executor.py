import time
from enum import Enum
from typing import Optional, TYPE_CHECKING

from loguru import logger

from src.execution.action_executor import ActionExecutor
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine
from src.planning.models import Plan, Task, TaskStatus
from src.planning.repair_engine import RepairEngine
from src.planning.validator import Validator

if TYPE_CHECKING:
    from src.perception.screen_capture import ScreenCapture
    from src.planning.htn_cache import HTNPlanCache


class FailureSeverity(Enum):
    RECOVERABLE = "recoverable"
    TERMINAL = "terminal"
    CRITICAL = "critical"


class PlanExecutor:
    def __init__(
        self,
        action_executor: ActionExecutor,
        policy_engine: PolicyEngine,
        validator: Optional[Validator] = None,
        repair_engine: Optional[RepairEngine] = None,
        screen_capture: Optional["ScreenCapture"] = None,
        cache: Optional["HTNPlanCache"] = None,
    ) -> None:
        self.executor = action_executor
        self.policy = policy_engine
        self.validator = validator
        self.repair = repair_engine
        self.screen = screen_capture
        self.cache = cache
        self._current_goal_text: Optional[str] = None
        self._last_severity: Optional[FailureSeverity] = None

    async def execute_plan(self, plan: Plan, goal_text: Optional[str] = None) -> bool:
        plan.status = TaskStatus.RUNNING
        logger.info(f"Executing plan: {plan.goal}")

        self._current_goal_text = goal_text or plan.goal
        self._last_severity = None

        pre_screenshot = await self._capture_screenshot()
        success = await self._execute_task(plan.root_task, pre_screenshot)

        plan.status = TaskStatus.SUCCESS if success else TaskStatus.FAILED
        logger.info(f"Plan {plan.plan_id}: {plan.status.value}")
        return success

    async def _execute_task(self, task: Task, pre_screenshot: bytes, depth: int = 0) -> bool:
        indent = "  " * depth
        task.status = TaskStatus.RUNNING
        logger.info(f"{indent}Task: {task.name} ({task.action_type or 'compound'})")

        if task.precondition and not await self._check_precondition(task.precondition):
            logger.warning(f"{indent}Precondition failed: {task.precondition}")
            task.status = TaskStatus.FAILED
            return False

        if task.subtasks:
            for subtask in task.subtasks:
                subtask.parent_id = task.task_id
                post_screenshot = await self._capture_screenshot()
                if not await self._execute_task(subtask, post_screenshot, depth + 1):
                    return False
        else:
            result = await self._execute_action(task)
            if not result:
                return False

        if task.postcondition:
            post_screenshot = await self._capture_screenshot()
            valid = await self.validator.validate(task, pre_screenshot, post_screenshot) if self.validator else True
            if not valid:
                logger.warning(f"{indent}Postcondition failed: {task.postcondition}")
                return False

        task.status = TaskStatus.SUCCESS
        logger.info(f"{indent}Task {task.name}: success")
        return True

    async def _execute_action(self, task: Task) -> bool:
        decision = await self.policy.evaluate_action(
            task.action_type, task.parameters, {},
        )
        if decision == PolicyDecision.BLOCK:
            logger.error(f"Action blocked by policy: {task.name}")
            task.status = TaskStatus.FAILED
            return False

        result, _ = await self.executor.execute_with_policy(
            task.action_type, task.parameters, self.policy, {},
        )
        if not result:
            task.status = TaskStatus.FAILED
            if task.action_type:
                severity = self._classify_failure(task.action_type, task.parameters)
                self._last_severity = severity
                if severity == FailureSeverity.TERMINAL:
                    self._invalidate_cache()
                elif severity == FailureSeverity.CRITICAL:
                    self._invalidate_cache()
            return await self._repair_task(task)

        return True

    def _classify_failure(self, action_type: str, params: dict) -> FailureSeverity:
        error = str(params)
        error_lower = error.lower()

        recoverable_patterns = ["timeout", "connection", "refused", "temporarily", "retry"]
        for pattern in recoverable_patterns:
            if pattern in error_lower:
                return FailureSeverity.RECOVERABLE

        terminal_patterns = ["not found", "no such element", "invalid selector", "does not exist"]
        for pattern in terminal_patterns:
            if pattern in error_lower:
                return FailureSeverity.TERMINAL

        critical_actions = {"delete", "remove", "confirm_destructive", "submit_critical"}
        if action_type in critical_actions:
            return FailureSeverity.CRITICAL

        return FailureSeverity.TERMINAL

    def _invalidate_cache(self) -> None:
        if self.cache and self._current_goal_text:
            self.cache.invalidate(self._current_goal_text)

    async def _repair_task(self, task: Task) -> bool:
        if self.repair:
            task.status = TaskStatus.REPAIRING
            success, strategy = await self.repair.repair(task, Exception("Action failed"), {})
            if success:
                return True
        return False

    async def _check_precondition(self, condition: str) -> bool:
        return True

    async def _capture_screenshot(self) -> bytes:
        if self.screen:
            return await self.screen.capture()
        return b""
