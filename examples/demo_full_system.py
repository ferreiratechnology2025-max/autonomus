"""Demonstrates the complete Jarvis v3 system: initialization, task processing, and calibration."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import Settings, load_settings
from src.core.health import HealthChecker
from src.governance.calibration_models import CalibrationSignal
from src.governance.calibration_loop import CalibrationLoop
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine
from src.planning.htn_decomposer import HTNDecomposer
from src.planning.models import Plan, TaskStatus
from src.planning.plan_executor import PlanExecutor


async def main():
    print("=== Jarvis v3 Full System Demo ===\n")

    # 1) Health check
    print("--- 1. Health Check ---")
    settings = load_settings()
    health = HealthChecker(settings)
    status = health.get_status()
    for name, check in status["checks"].items():
        print(f"  {name}: {check['status']}")
    print(f"  overall: {status['status']}\n")

    # 2) Policy engine with calibration
    print("--- 2. Policy Engine + Calibration ---")
    policy = PolicyEngine(settings)
    cal = CalibrationLoop(policy, config=settings)
    policy.calibration_loop = cal

    print(f"  Initial weights: {cal.weights}")

    # Simulate feedback: sensitive data was handled successfully
    signal = CalibrationSignal(
        action_hash="type_password",
        risk_features={"sensitive_data_detected": 0.5},
        outcome="success",
    )
    await cal.record_feedback(signal)
    print(f"  After success feedback: weight sensitive_data_detected = {cal.weights['sensitive_data_detected']:.3f}")

    # Simulate feedback: destructive action failed
    signal2 = CalibrationSignal(
        action_hash="delete_file",
        risk_features={"action_is_destructive": 0.4},
        outcome="failed",
    )
    await cal.record_feedback(signal2)
    print(f"  After failure feedback: weight action_is_destructive = {cal.weights['action_is_destructive']:.3f}")

    # 3) HTN decomposition
    print("\n--- 3. HTN Decomposition ---")
    decomposer = HTNDecomposer()
    task = await decomposer.decompose("open_app", {"app_name": "calculator"})
    print(f"  Goal 'open calculator': {len(task.subtasks)} subtasks")
    for st in task.subtasks:
        print(f"    -> {st.name}: {st.action_type} {st.parameters}")

    # 4) Policy evaluation
    print("\n--- 4. Policy Evaluation ---")
    for action, params, desc in [
        ("click", {"x": 500, "y": 500}, "safe click"),
        ("type_text", {"text": "password = secret"}, "sensitive text"),
        ("type_text", {"text": "rm -rf /data"}, "dangerous text"),
        ("screenshot", {}, "screenshot"),
    ]:
        decision, sig = await policy.evaluate_action_with_calibration(action, params, {})
        print(f"  {desc:20s}: {decision.value}")

    # 5) Full goal execution
    print("\n--- 5. Goal Execution (mocked) ---")
    from unittest.mock import AsyncMock, MagicMock

    executor = MagicMock()
    executor.execute_with_policy = AsyncMock(return_value=(True, PolicyDecision.ALLOW))

    plan_executor = PlanExecutor(
        action_executor=executor,
        policy_engine=policy,
    )

    plan = Plan(goal="open calculator demo", root_task=task)
    success = await plan_executor.execute_plan(plan)
    print(f"  Plan execution: {'SUCCESS' if success else 'FAILED'}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
