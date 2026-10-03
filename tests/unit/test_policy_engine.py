from unittest.mock import MagicMock, patch

import pytest

from src.core.config import Settings
from src.governance.models import PolicyDecision, RiskLevel
from src.governance.policy_engine import PolicyEngine
from src.governance.sensitive_detector import SensitiveDataDetector


@pytest.fixture
def settings():
    return Settings(
        enable_policy_engine=True,
        sensitive_detection_enabled=True,
        require_confirm_high_risk=True,
        require_confirm_medium_risk=False,
    )


@pytest.fixture
def engine(settings):
    return PolicyEngine(settings)


@pytest.mark.asyncio
async def test_evaluate_allows_safe_action(engine):
    decision = await engine.evaluate_action(
        "click", {"x": 500, "y": 500}, {"app": "notepad"},
    )
    assert decision == PolicyDecision.ALLOW


@pytest.mark.asyncio
async def test_evaluate_blocks_critical_with_password(engine):
    decision = await engine.evaluate_action(
        "type_text", {"text": "password = hunter2"}, {},
    )
    assert decision == PolicyDecision.BLOCK


@pytest.mark.asyncio
async def test_evaluate_blocks_dangerous_keyword(engine):
    decision = await engine.evaluate_action(
        "type_text", {"text": "rm -rf /"}, {},
    )
    assert decision == PolicyDecision.BLOCK


@pytest.mark.asyncio
async def test_evaluate_confirm_high_risk(engine):
    decision = await engine.evaluate_action(
        "click", {"button_text": "Delete all files"}, {},
    )
    assert decision == PolicyDecision.CONFIRM


@pytest.mark.asyncio
async def test_evaluate_returns_allow_when_disabled():
    settings = Settings(enable_policy_engine=False)
    engine = PolicyEngine(settings)
    decision = await engine.evaluate_action(
        "type_text", {"text": "password = hunter2"}, {},
    )
    assert decision == PolicyDecision.ALLOW


def test_record_override(engine):
    engine.record_override("user1", "action1", PolicyDecision.ALLOW, "manual override")
    assert len(engine.override_history) == 1
    assert engine.override_history[0].user_id == "user1"


@pytest.mark.asyncio
async def test_should_route_to_private_model_with_sensitive_prompt(engine):
    result = await engine.should_route_to_private_model("my email is test@example.com")
    assert result is True


@pytest.mark.asyncio
async def test_should_route_to_private_model_with_safe_prompt(engine):
    result = await engine.should_route_to_private_model("what time is it?")
    assert result is False


@pytest.mark.asyncio
async def test_should_route_to_private_model_with_sensitive_screenshot(engine):
    with patch.object(engine.sensitive_detector, "detect_in_image") as mock_detect:
        mock_detect.return_value = [{"type": "email", "value": "foo@bar.com", "position": (0, 5)}]
        result = await engine.should_route_to_private_model("describe this", b"fake-image")
        assert result is True


def test_get_health_status(engine):
    status = engine.get_health_status()
    assert status["enabled"] is True
    assert status["sensitive_detection"] is True
    assert status["overrides_logged"] == 0


@pytest.mark.asyncio
async def test_evaluate_sensitive_detection_in_params(engine):
    decision = await engine.evaluate_action(
        "type_text", {"text": "forward this to foo@bar.com"}, {},
    )
    assert decision == PolicyDecision.BLOCK
