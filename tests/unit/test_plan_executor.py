from unittest.mock import AsyncMock, MagicMock

import pytest

from src.execution.action_executor import ActionExecutor
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine
from src.planning.models import Plan, Task, TaskStatus
from src.planning.plan_executor import PlanExecutor
from src.planning.repair_engine import RepairEngine
from src.planning.validator import Validator


@pytest.fixture
def mock_executor():
    executor = MagicMock(spec=ActionExecutor)
    executor.execute_with_policy = AsyncMock(return_value=(True, PolicyDecision.ALLOW))
    return executor


@pytest.fixture
def mock_policy():
    policy = MagicMock(spec=PolicyEngine)
    policy.evaluate_action = AsyncMock(return_value=PolicyDecision.ALLOW)
    return policy


@pytest.fixture
def plan_executor(mock_executor, mock_policy):
    return PlanExecutor(
        action_executor=mock_executor,
        policy_engine=mock_policy,
    )


@pytest.mark.asyncio
async def test_execute_plan_simple_success(plan_executor):
    task = Task(name="click", action_type="click", parameters={"x": 100, "y": 100})
    plan = Plan(goal="test", root_task=task)
    success = await plan_executor.execute_plan(plan)
    assert success is True
    assert plan.status == TaskStatus.SUCCESS


@pytest.mark.asyncio
async def test_execute_plan_compound_task(plan_executor):
    subtask = Task(name="sub_click", action_type="click", parameters={"x": 50, "y": 50})
    root = Task(name="compound", subtasks=[subtask])
    plan = Plan(goal="compound_test", root_task=root)
    success = await plan_executor.execute_plan(plan)
    assert success is True


@pytest.mark.asyncio
async def test_execute_task_blocked_by_policy(plan_executor, mock_policy):
    mock_policy.evaluate_action = AsyncMock(return_value=PolicyDecision.BLOCK)
    task = Task(name="blocked", action_type="click", parameters={"x": 0, "y": 0})
    plan = Plan(goal="block_test", root_task=task)
    success = await plan_executor.execute_plan(plan)
    assert success is False
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_execute_action_failure_triggers_repair(plan_executor, mock_executor):
    mock_executor.execute_with_policy = AsyncMock(return_value=(False, PolicyDecision.ALLOW))
    task = Task(name="failing", action_type="click", parameters={"x": 100, "y": 100})
    plan = Plan(goal="fail_test", root_task=task)
    success = await plan_executor.execute_plan(plan)
    assert success is False


@pytest.mark.asyncio
async def test_execute_plan_validates_postcondition(plan_executor, mock_executor):
    mock_executor.execute_with_policy = AsyncMock(return_value=(True, PolicyDecision.ALLOW))
    validator = MagicMock(spec=Validator)
    validator.validate = AsyncMock(return_value=True)
    plan_executor.validator = validator

    task = Task(name="validated", action_type="click", postcondition="window_changed")
    plan = Plan(goal="validate_test", root_task=task)
    success = await plan_executor.execute_plan(plan)
    assert success is True


@pytest.mark.asyncio
async def test_execute_plan_postcondition_fails(plan_executor, mock_executor):
    validator = MagicMock(spec=Validator)
    validator.validate = AsyncMock(return_value=False)
    plan_executor.validator = validator

    task = Task(name="bad", action_type="click", postcondition="text_appeared")
    plan = Plan(goal="bad", root_task=task)
    success = await plan_executor.execute_plan(plan)
    assert success is False


def test_plan_initial_status_pending():
    plan = Plan(goal="test")
    assert plan.status == TaskStatus.PENDING


def test_task_defaults():
    task = Task(name="test")
    assert task.status == TaskStatus.PENDING
    assert task.subtasks == []
