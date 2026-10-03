from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.planning.htn_decomposer import HTNDecomposer
from src.planning.models import Plan
from src.planning.plan_executor import PlanExecutor
from src.planning.validator import Validator


@pytest.fixture
def _settings():
    return Settings()


@pytest.fixture
def router(_settings):
    return ModelRouter(_settings)


@pytest.fixture
def detector():
    return SensitiveDataDetector()


@pytest.mark.asyncio
async def test_decompose_and_execute_simple_goal(router, detector):
    decomposer = HTNDecomposer(router, detector)
    task = await decomposer.decompose("open_app", {"app_name": "notepad"})
    assert len(task.subtasks) == 3

    with patch("src.execution.action_executor.ActionExecutor.execute_with_policy") as mock_exec:
        mock_exec.return_value = (True, PolicyDecision.ALLOW)
        executor = MagicMock()
        executor.execute_with_policy = mock_exec

        policy = PolicyEngine(Settings())
        plan_executor = PlanExecutor(
            action_executor=executor,
            policy_engine=policy,
        )

        plan = Plan(goal="open notepad", root_task=task)
        success = await plan_executor.execute_plan(plan)
        assert success is True


@pytest.mark.asyncio
async def test_orchestrator_execute_goal():
    from src.core.orchestrator import JarvisOrchestrator

    orch = JarvisOrchestrator(Settings())
    orch.planner = MagicMock()
    orch.planner.decompose = AsyncMock(return_value=MagicMock(subtasks=[]))
    orch.plan_executor = MagicMock()
    orch.plan_executor.execute_plan = AsyncMock(return_value=True)

    result = await orch.execute_goal("test goal", {"key": "value"})
    assert result["success"] is True
    assert "plan_id" in result


@pytest.mark.asyncio
async def test_full_decompose_and_execute_chain(router, detector):
    decomposer = HTNDecomposer(router, detector)
    task = await decomposer.decompose("login", {"username": "user", "password": "pass"})
    assert task.name == "login"

    policy = PolicyEngine(Settings())
    policy.evaluate_action = AsyncMock(return_value=PolicyDecision.ALLOW)

    executor = MagicMock()
    executor.execute_with_policy = AsyncMock(return_value=(True, PolicyDecision.ALLOW))

    plan_executor = PlanExecutor(
        action_executor=executor,
        policy_engine=policy,
    )

    plan = Plan(goal="login test", root_task=task)
    success = await plan_executor.execute_plan(plan)
    assert success is True
