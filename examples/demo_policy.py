"""Demonstrates Policy Engine: blocking dangerous actions, sensitive data detection, and overrides."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import Settings
from src.governance.models import PolicyDecision
from src.governance.policy_engine import PolicyEngine
from src.governance.risk_rules import RiskRules
from src.governance.sensitive_detector import SensitiveDataDetector


async def main():
    settings = Settings(
        enable_policy_engine=True,
        sensitive_detection_enabled=True,
        require_confirm_high_risk=True,
    )
    engine = PolicyEngine(settings)

    # 1) Safe action
    print("--- 1. Safe action (click x=500 y=500) ---")
    decision = await engine.evaluate_action("click", {"x": 500, "y": 500}, {"app": "notepad"})
    print(f"  Decision: {decision.value}")
    assert decision == PolicyDecision.ALLOW

    # 2) Password detected → BLOCK
    print("--- 2. Password in text ---")
    decision = await engine.evaluate_action("type_text", {"text": "password = hunter2"}, {})
    print(f"  Decision: {decision.value}")
    assert decision == PolicyDecision.BLOCK

    # 3) Dangerous keyword → BLOCK
    print("--- 3. Dangerous keyword 'rm -rf' ---")
    decision = await engine.evaluate_action("type_text", {"text": "rm -rf /data"}, {})
    print(f"  Decision: {decision.value}")
    assert decision == PolicyDecision.BLOCK

    # 4) High risk button → CONFIRM
    print("--- 4. Destructive button click ---")
    decision = await engine.evaluate_action("click", {"button_text": "Delete all"}, {})
    print(f"  Decision: {decision.value}")
    assert decision == PolicyDecision.CONFIRM

    # 5) Screenshot → MEDIUM (no confirm by default)
    print("--- 5. Screenshot ---")
    decision = await engine.evaluate_action("screenshot", {}, {})
    print(f"  Decision: {decision.value}")

    # 6) Private model routing
    print("--- 6. Sensitive data -> private model ---")
    assert await engine.should_route_to_private_model("email: test@example.com") is True
    print("  Sensitive prompt routed to private model: True")
    assert await engine.should_route_to_private_model("what is the weather?") is False
    print("  Safe prompt routed to private model: False")

    # 7) Override recording
    print("--- 7. User override ---")
    engine.record_override("user1", "action_delete_1", PolicyDecision.ALLOW, "user confirmed")
    print(f"  Overrides logged: {len(engine.override_history)}")

    # 8) Health status
    print("--- 8. Policy engine health ---")
    health = engine.get_health_status()
    for k, v in health.items():
        print(f"  {k}: {v}")

    print("\nAll policy checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
