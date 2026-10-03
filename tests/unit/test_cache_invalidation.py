import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.governance.models import PolicyDecision
from src.planning.htn_cache import HTNPlanCache
from src.planning.models import Plan, Task
from src.planning.plan_executor import FailureSeverity, PlanExecutor


@pytest.fixture
def cache(tmp_path: Path):
    return HTNPlanCache(db_path=str(tmp_path / "test_cache.db"))


def test_cache_invalidation(cache: HTNPlanCache):
    cache.set("Testar sistema", [{"action_type": "click", "parameters": {"selector": "#btn"}}])
    assert cache.get("Testar sistema") is not None
    cache.invalidate("Testar sistema")
    assert cache.get("Testar sistema") is None


def test_cache_invalidation_by_hash(cache: HTNPlanCache):
    cache.set("Objetivo único", [{"action_type": "click", "parameters": {}}])
    obj_hash = cache.get_hash("Objetivo único")
    assert cache.invalidate_by_hash(obj_hash) is True
    assert cache.get("Objetivo único") is None


def test_invalidate_nonexistent(cache: HTNPlanCache):
    assert cache.invalidate("Não existe") is False


def test_get_hash_consistency(cache: HTNPlanCache):
    h1 = cache.get_hash("  Abrir Chrome  ")
    h2 = cache.get_hash("abrir chrome")
    assert h1 == h2


def test_classify_recoverable():
    executor = PlanExecutor(
        action_executor=MagicMock(),
        policy_engine=MagicMock(),
    )
    assert executor._classify_failure("click", {"error": "Timeout after 30s"}) == FailureSeverity.RECOVERABLE
    assert executor._classify_failure("click", {"error": "Connection refused"}) == FailureSeverity.RECOVERABLE
    assert executor._classify_failure("navigate", {"error": "temporarily unavailable"}) == FailureSeverity.RECOVERABLE


def test_classify_terminal():
    executor = PlanExecutor(
        action_executor=MagicMock(),
        policy_engine=MagicMock(),
    )
    assert executor._classify_failure("browser_click", {"error": "Element not found"}) == FailureSeverity.TERMINAL
    assert executor._classify_failure("browser_type", {"error": "Invalid selector"}) == FailureSeverity.TERMINAL
    assert executor._classify_failure("click", {"error": "No such element #btn"}) == FailureSeverity.TERMINAL
    assert executor._classify_failure("navigate", {"error": "does not exist"}) == FailureSeverity.TERMINAL


def test_classify_critical():
    executor = PlanExecutor(
        action_executor=MagicMock(),
        policy_engine=MagicMock(),
    )
    assert executor._classify_failure("delete", {"error": "any"}) == FailureSeverity.CRITICAL
    assert executor._classify_failure("remove", {"error": "any"}) == FailureSeverity.CRITICAL
    assert executor._classify_failure("confirm_destructive", {"error": "any"}) == FailureSeverity.CRITICAL


def test_classify_defaults_to_terminal():
    executor = PlanExecutor(
        action_executor=MagicMock(),
        policy_engine=MagicMock(),
    )
    assert executor._classify_failure("unknown_action", {"error": "strange error"}) == FailureSeverity.TERMINAL


@pytest.mark.asyncio
async def test_cache_invalidation_on_terminal_failure(cache: HTNPlanCache):
    mock_executor = MagicMock()
    mock_executor.execute_with_policy = AsyncMock(return_value=(False, PolicyDecision.ALLOW))
    mock_policy = MagicMock()
    mock_policy.evaluate_action = AsyncMock(return_value=PolicyDecision.ALLOW)

    executor = PlanExecutor(
        action_executor=mock_executor,
        policy_engine=mock_policy,
        cache=cache,
    )

    bad_plan = [{"action_type": "click", "parameters": {"selector": "#elemento-inexistente"}}]
    cache.set("Clicar no botão", bad_plan)
    assert cache.get("Clicar no botão") is not None

    task = Task(name="click", action_type="click", parameters={"error": "Element not found: #btn"})
    plan = Plan(goal="Clicar no botão", root_task=task)
    result = await executor.execute_plan(plan, goal_text="Clicar no botão")

    assert result is False
    assert cache.get("Clicar no botão") is None


@pytest.mark.asyncio
async def test_cache_preserved_on_recoverable_failure(cache: HTNPlanCache):
    mock_executor = MagicMock()
    mock_executor.execute_with_policy = AsyncMock(return_value=(False, PolicyDecision.ALLOW))
    mock_policy = MagicMock()
    mock_policy.evaluate_action = AsyncMock(return_value=PolicyDecision.ALLOW)

    executor = PlanExecutor(
        action_executor=mock_executor,
        policy_engine=mock_policy,
        cache=cache,
    )

    actions = [{"action_type": "navigate", "parameters": {"url": "https://example.com"}}]
    cache.set("Acessar site", actions)
    assert cache.get("Acessar site") is not None

    task = Task(name="navigate", action_type="navigate", parameters={"error": "Timeout after 30s"})
    plan = Plan(goal="Acessar site", root_task=task)
    result = await executor.execute_plan(plan, goal_text="Acessar site")

    assert result is False
    assert cache.get("Acessar site") is not None
