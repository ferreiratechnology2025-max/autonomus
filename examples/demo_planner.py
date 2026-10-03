"""Demonstrates HTN planning: decompose goals into subtasks and execute step by step."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import Settings
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine
from src.planning.htn_decomposer import HTNDecomposer
from src.planning.models import Plan, TaskStatus
from src.planning.plan_executor import PlanExecutor
from src.planning.repair_engine import RepairEngine
from src.planning.validator import Validator


async def main():
    settings = Settings()

    # 1) Decompose "open_app notepad"
    print("=== 1. Decompose: open_app notepad ===")
    decomposer = HTNDecomposer()
    task = await decomposer.decompose("open_app", {"app_name": "notepad"})
    print(f"Root task: {task.name} ({len(task.subtasks)} subtasks)")
    for st in task.subtasks:
        print(f"  -> {st.name:20s} {st.action_type:15s} {st.parameters}")

    # 2) Decompose "login"
    print("\n=== 2. Decompose: login ===")
    task2 = await decomposer.decompose("login", {"username": "admin", "password": "***"})
    print(f"Root task: {task2.name} ({len(task2.subtasks)} subtasks)")
    for st in task2.subtasks:
        print(f"  -> {st.name:20s} {st.action_type:15s} {st.parameters}")

    # 3) Decompose unknown goal (fallback)
    print("\n=== 3. Unknown goal (fallback) ===")
    task3 = await decomposer.decompose("do something random")
    print(f"Root task: {task3.name} ({len(task3.subtasks)} subtasks)")

    # 4) Execute a simple plan
    print("\n=== 4. Execute simple click plan ===")
    from unittest.mock import AsyncMock, MagicMock

    executor = MagicMock()
    executor.execute_with_policy = AsyncMock(return_value=(True, PolicyDecision.ALLOW))
    policy = PolicyEngine(settings)

    plan_executor = PlanExecutor(
        action_executor=executor,
        policy_engine=policy,
        validator=Validator(),
    )

    plan = Plan(goal="click test", root_task=task)
    success = await plan_executor.execute_plan(plan)
    print(f"Plan execution: {'SUCCESS' if success else 'FAILED'}")
    print(f"Plan status: {plan.status.value}")

    # 5) Test repair on failure
    print("\n=== 5. Repair on failure ===")
    executor.execute_with_policy = AsyncMock(return_value=(False, PolicyDecision.ALLOW))
    repair = RepairEngine()

    plan_executor2 = PlanExecutor(
        action_executor=executor,
        policy_engine=policy,
        repair_engine=repair,
    )

    fail_plan = Plan(goal="fail test", root_task=task)
    success2 = await plan_executor2.execute_plan(fail_plan)
    print(f"After repair: {'RECOVERED' if success2 else 'FAILED'}")
    print(f"Plan status: {fail_plan.status.value}")

    # 6) Goal similarity test
    print("\n=== 6. Goal similarity ===")
    print(f"  'open notepad' ~ 'open notepad and type': {decomposer._goal_similar('open notepad', 'open notepad and type')}")
    print(f"  'open notepad' ~ 'delete files': {decomposer._goal_similar('open notepad', 'delete files')}")

    print("\nAll planner checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
