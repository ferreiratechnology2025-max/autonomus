from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.core.orchestrator import JarvisOrchestrator
from src.governance.calibration_loop import CalibrationLoop
from src.governance.calibration_models import CalibrationSignal
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine


@pytest.fixture
def settings():
    return Settings(
        calibration_enabled=True,
        calibration_alpha=0.1,
        calibration_learning_rate=0.05,
    )


@pytest.mark.asyncio
async def test_policy_evaluate_with_calibration_returns_signal(settings):
    policy = PolicyEngine(settings)
    decision, signal = await policy.evaluate_action_with_calibration(
        "click", {"x": 500, "y": 500}, {"app": "test"},
    )
    assert decision == PolicyDecision.ALLOW
    assert signal.action_hash != ""
    assert signal.risk_features != {}


@pytest.mark.asyncio
async def test_calibration_loop_integration(settings):
    policy = PolicyEngine(settings)
    cal = CalibrationLoop(policy, config=settings)
    cal._save_weights = AsyncMock()
    policy.calibration_loop = cal

    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"action_is_destructive": 0.4},
        outcome="failed",
    )
    await policy.update_with_feedback(signal)
    assert cal.weights.get("action_is_destructive", 0.0) > 0.4


@pytest.mark.asyncio
async def test_orchestrator_initializes_calibration(settings):
    orch = JarvisOrchestrator(settings)
    await orch.initialize()
    assert orch.calibration is not None
    assert orch.policy.calibration_loop is not None


@pytest.mark.asyncio
async def test_health_check_includes_calibration(settings):
    from src.core.health import HealthChecker

    checker = HealthChecker(settings)
    status = checker.get_status()
    assert "calibration" in status["checks"]


@pytest.mark.asyncio
async def test_executor_with_calibration_flow(settings):
    policy = PolicyEngine(settings)
    cal = CalibrationLoop(policy, config=settings)
    cal._save_weights = AsyncMock()
    policy.calibration_loop = cal

    with patch("src.execution.action_executor.ActionExecutor._dispatch", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = True
        from src.execution.action_executor import ActionExecutor

        executor = ActionExecutor(settings)
        result, decision, signal = await executor.execute_with_calibration(
            "click", {"x": 500, "y": 500}, policy, {"app": "test"},
        )
        assert result is True
        assert decision == PolicyDecision.ALLOW
        assert signal.outcome == "success"


@pytest.mark.asyncio
async def test_main_loop_initializes_orchestrator(settings):
    from src.core.main_loop import JarvisMainLoop

    orch = MagicMock()
    orch.initialize = AsyncMock()
    with (
        patch.object(orch, "execute_goal", new_callable=AsyncMock) as mock_exec,
    ):
        mock_exec.return_value = {"success": True, "plan_id": "test"}
        loop = JarvisMainLoop(orch, settings)
        loop.running = False
        assert loop.orchestrator is orch
