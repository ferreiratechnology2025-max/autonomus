from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine


@pytest.fixture
def settings():
    return Settings(
        enable_policy_engine=True,
        sensitive_detection_enabled=True,
        require_confirm_high_risk=True,
    )


@pytest.mark.asyncio
async def test_policy_blocks_and_executor_returns_false(settings):
    engine = PolicyEngine(settings)
    with patch("src.execution.action_executor.ActionExecutor._dispatch", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = True
        from src.execution.action_executor import ActionExecutor

        executor = ActionExecutor(settings)
        result, decision = await executor.execute_with_policy(
            "type_text",
            {"text": "password = secret"},
            engine,
            {"app": "login"},
        )
    assert result is False
    assert decision == PolicyDecision.BLOCK
    mock_dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_policy_allows_and_executor_executes(settings):
    engine = PolicyEngine(settings)
    with patch("src.execution.action_executor.ActionExecutor._dispatch", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = True
        from src.execution.action_executor import ActionExecutor

        executor = ActionExecutor(settings)
        result, decision = await executor.execute_with_policy(
            "click",
            {"x": 500, "y": 500},
            engine,
            {"app": "notepad"},
        )
    assert result is True
    assert decision == PolicyDecision.ALLOW
    mock_dispatch.assert_called_once_with("click", {"x": 500, "y": 500})


@pytest.mark.asyncio
async def test_policy_confirm_and_executor_executes(settings):
    engine = PolicyEngine(settings)
    with patch("src.execution.action_executor.ActionExecutor._dispatch", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = True
        from src.execution.action_executor import ActionExecutor

        executor = ActionExecutor(settings)
        result, decision = await executor.execute_with_policy(
            "click",
            {"button_text": "Delete all"},
            engine,
            {"app": "filemanager"},
        )
    assert result is True
    assert decision == PolicyDecision.CONFIRM
    mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_includes_policy(settings):
    from src.core.health import HealthChecker

    checker = HealthChecker(settings)
    status = checker.get_status()
    assert "policy" in status["checks"]
    assert status["checks"]["policy"]["status"] == "healthy"
