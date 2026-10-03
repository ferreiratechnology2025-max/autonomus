from typing import Optional

from loguru import logger

from src.core.approval import ApprovalHandler
from src.core.config import Settings
from src.core.health import HealthChecker
from src.execution.action_executor import ActionExecutor
from src.governance.calibration_loop import CalibrationLoop
from src.governance.policy_engine import PolicyEngine
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.browser_manager import get_browser_manager
from src.integration.model_router import ModelRouter
from src.memory.memory import MemorySystem
from src.planning.htn_cache import HTNPlanCache
from src.planning.htn_decomposer import HTNDecomposer
from src.planning.plan_executor import PlanExecutor, FailureSeverity
from src.planning.repair_engine import RepairEngine
from src.planning.validator import Validator
from src.core.metrics import get_metrics
from src.planning.models import Plan


class JarvisOrchestrator:
    def __init__(self, config: Settings, approval_handler: Optional[ApprovalHandler] = None) -> None:
        self.config = config
        self.approval_handler = approval_handler
        self.executor: Optional[ActionExecutor] = None
        self.memory: Optional[MemorySystem] = None
        self.policy: Optional[PolicyEngine] = None
        self.model_router: Optional[ModelRouter] = None
        self.planner: Optional[HTNDecomposer] = None
        self.plan_executor: Optional[PlanExecutor] = None
        self.validator: Optional[Validator] = None
        self.repair: Optional[RepairEngine] = None
        self.calibration: Optional[CalibrationLoop] = None
        self.sensitive_detector: Optional[SensitiveDataDetector] = None

    async def initialize(self) -> None:
        logger.info("Initializing JarvisOrchestrator...")

        self.executor = ActionExecutor(self.config, approval_handler=self.approval_handler)
        self.validator = Validator()
        self.policy = PolicyEngine(self.config)
        self.sensitive_detector = SensitiveDataDetector()

        self.cache = HTNPlanCache()

        if self.config.calibration_enabled:
            self.calibration = CalibrationLoop(
                policy_engine=self.policy,
                config=self.config,
            )
            self.policy.calibration_loop = self.calibration

        self.plan_executor = PlanExecutor(
            action_executor=self.executor,
            policy_engine=self.policy,
            validator=self.validator,
            cache=self.cache,
        )

        openrouter_client = None
        if self.config.openrouter_enabled:
            from src.integration.openrouter_client import OpenRouterClient
            openrouter_client = OpenRouterClient(self.config)

        self.model_router = ModelRouter(self.config, openrouter_client)

        self.planner = HTNDecomposer(
            model_router=self.model_router,
            sensitive_detector=self.sensitive_detector,
            cache=self.cache,
        )
        self.repair = RepairEngine(
            model_router=self.model_router,
            sensitive_detector=self.sensitive_detector,
        )

        logger.info("JarvisOrchestrator initialized")

    async def execute_goal(self, goal: str, context: Optional[dict] = None) -> dict:
        logger.info(f"Executing goal: {goal}")

        plan = await self.planner.decompose(goal, context or {})
        plan_obj = Plan(goal=goal, root_task=plan)

        success = await self.plan_executor.execute_plan(plan_obj, goal_text=goal)

        if not success and self.plan_executor._last_severity in (
            FailureSeverity.TERMINAL, FailureSeverity.CRITICAL,
        ):
            health = await self._check_session_health()
            if health["is_healthy"]:
                logger.info(f"Falha terminal em {goal[:50]}... sessão saudavel, regenerando plano")
                plan = await self.planner.decompose(goal, context or {})
                plan_obj = Plan(goal=goal, root_task=plan)
                success = await self.plan_executor.execute_plan(plan_obj, goal_text=goal)
            else:
                logger.warning(f"Falha terminal em {goal[:50]}... sessão comprometida, abortando retry")
                for s in health["signals"]:
                    logger.warning(f"  Sinal de saude: {s}")
                get_metrics().increment("retry_aborted_unhealthy_session")

        return {"success": success, "plan_id": plan_obj.plan_id}

    async def _check_session_health(self) -> dict:
        result = {"is_healthy": True, "signals": []}

        browser = get_browser_manager()
        if browser.is_connected:
            health = await browser.check_health()
            if not health["is_healthy"]:
                result["is_healthy"] = False
                result["signals"].extend(health["signals"])

        try:
            import ctypes
            _user32 = ctypes.windll.user32
            fg = _user32.GetForegroundWindow()
            if fg == 0:
                result["signals"].append("no_foreground_window")
                result["is_healthy"] = False
        except Exception as e:
            logger.warning(f"_check_session_health: falha ao ler foreground window: {e}")

        return result

    async def health_check(self) -> dict:
        checker = HealthChecker(self.config)
        return checker.get_status()

    def get_metrics_snapshot(self) -> dict:
        return get_metrics().snapshot()

    async def shutdown(self) -> None:
        logger.info("Shutting down orchestrator...")
