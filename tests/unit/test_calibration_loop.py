from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import Settings
from src.governance.calibration_loop import CalibrationLoop
from src.governance.calibration_models import CalibrationSignal
from src.governance.policy_engine import PolicyEngine


@pytest.fixture
def config():
    return Settings(
        calibration_enabled=True,
        calibration_alpha=0.1,
        calibration_learning_rate=0.05,
    )


@pytest.fixture
def policy(config):
    return PolicyEngine(config)


@pytest.mark.asyncio
async def test_record_feedback_success_reduces_weights(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    old_value = cal.weights.get("sensitive_data_detected", 0.5)

    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"sensitive_data_detected": 0.5},
        outcome="success",
    )
    await cal.record_feedback(signal)

    new_value = cal.weights.get("sensitive_data_detected", 0.5)
    assert new_value < old_value


@pytest.mark.asyncio
async def test_record_feedback_failure_increases_weights(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    old_value = cal.weights.get("action_is_destructive", 0.4)

    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"action_is_destructive": 0.4},
        outcome="failed",
    )
    await cal.record_feedback(signal)

    new_value = cal.weights.get("action_is_destructive", 0.4)
    assert new_value > old_value


@pytest.mark.asyncio
async def test_record_feedback_skips_ambiguous_outcomes(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    old = dict(cal.weights)

    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"sensitive_data_detected": 0.5},
        outcome="pending",
    )
    await cal.record_feedback(signal)

    assert cal.weights == old


@pytest.mark.asyncio
async def test_weights_EMA_maintains_stability(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"sensitive_data_detected": 0.5},
        outcome="success",
    )
    await cal.record_feedback(signal)
    ema_after_first = cal.predicted_risk_ema

    await cal.record_feedback(signal)
    ema_after_second = cal.predicted_risk_ema

    assert ema_after_second != ema_after_first


@pytest.mark.asyncio
async def test_reset_weights(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    cal.weights["sensitive_data_detected"] = 0.9
    await cal.reset_weights()
    assert cal.weights["sensitive_data_detected"] == 0.5


def test_default_weights(config, policy):
    cal = CalibrationLoop(policy, config=config)
    assert "sensitive_data_detected" in cal.weights
    assert "action_is_destructive" in cal.weights
    assert "window_changed" in cal.weights


def test_get_health_status(config, policy):
    cal = CalibrationLoop(policy, config=config)
    status = cal.get_health_status()
    assert status["enabled"] is True
    assert status["weights_count"] > 0


@pytest.mark.asyncio
async def test_record_feedback_empty_features(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    signal = CalibrationSignal(action_hash="test", risk_features={}, outcome="success")
    old = dict(cal.weights)
    await cal.record_feedback(signal)
    assert cal.weights == old


@pytest.mark.asyncio
async def test_record_feedback_user_approved(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    old = cal.weights.get("sensitive_data_detected", 0.5)
    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"sensitive_data_detected": 0.5},
        outcome="user_approved",
    )
    await cal.record_feedback(signal)
    assert cal.weights.get("sensitive_data_detected", 0.5) < old


@pytest.mark.asyncio
async def test_record_feedback_user_denied(config, policy):
    cal = CalibrationLoop(policy, config=config)
    cal._save_weights = AsyncMock()
    old = cal.weights.get("sensitive_data_detected", 0.5)
    signal = CalibrationSignal(
        action_hash="test",
        risk_features={"sensitive_data_detected": 0.5},
        outcome="user_denied",
    )
    await cal.record_feedback(signal)
    assert cal.weights.get("sensitive_data_detected", 0.5) > old
