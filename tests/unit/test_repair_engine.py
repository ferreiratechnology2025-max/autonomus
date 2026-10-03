from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.planning.models import RepairStrategy, Task, TaskStatus
from src.planning.repair_engine import RepairEngine


@pytest.fixture
def mock_router():
    router = MagicMock(spec=ModelRouter)
    router.generate = AsyncMock(
        return_value=MagicMock(
            text="try a different approach",
            model_used="ollama/test",
            cost=0.0,
            metadata={},
            success=True,
        )
    )
    return router


@pytest.fixture
def mock_detector():
    detector = MagicMock(spec=SensitiveDataDetector)
    detector.has_sensitive_data = MagicMock(return_value=False)
    return detector


@pytest.mark.asyncio
async def test_retry_succeeds(mock_router, mock_detector):
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test", action_type="click")
    calls = [False, False, True]
    original = engine._execute_action_simple

    async def mock_execute(*args):
        return calls.pop(0) if calls else True

    engine._execute_action_simple = mock_execute
    success, strategy = await engine.repair(task, Exception("fail"), {})
    assert success is True
    assert strategy == RepairStrategy.RETRY


@pytest.mark.asyncio
async def test_all_strategies_fail(mock_router, mock_detector):
    mock_router.generate = AsyncMock(
        return_value=MagicMock(text="", model_used="degraded", cost=0, metadata={}, success=False)
    )
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test", action_type="click")
    success, strategy = await engine.repair(task, Exception("fail"), {})
    assert success is False
    assert strategy == RepairStrategy.ABORT
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_retry_action_max_attempts(mock_router, mock_detector):
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test")
    engine._execute_action_simple = AsyncMock(return_value=False)
    result = await engine._try_strategy(RepairStrategy.RETRY, task, Exception("fail"), {})
    assert result is False


@pytest.mark.asyncio
async def test_escalate_llm_with_client(mock_router, mock_detector):
    mock_detector.has_sensitive_data = MagicMock(return_value=False)
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test")
    result = await engine._try_strategy(RepairStrategy.ESCALATE_LLM, task, Exception("fail"), {})
    assert result is True


@pytest.mark.asyncio
async def test_escalate_llm_no_client(mock_router, mock_detector):
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test")
    result = await engine._try_strategy(RepairStrategy.ESCALATE_LLM, task, Exception("fail"), {})
    assert result is True


@pytest.mark.asyncio
async def test_ask_user_returns_false(mock_router, mock_detector):
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test")
    result = await engine._try_strategy(RepairStrategy.ASK_USER, task, Exception("fail"), {})
    assert result is False


@pytest.mark.asyncio
async def test_alternative_returns_false(mock_router, mock_detector):
    engine = RepairEngine(mock_router, mock_detector)
    task = Task(name="test")
    result = await engine._try_strategy(RepairStrategy.ALTERNATIVE, task, Exception("fail"), {})
    assert result is False
