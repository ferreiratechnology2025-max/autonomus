import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.governance.calibration_models import CalibrationSignal
from src.governance.models import RiskLevel
from src.governance.simple_calibration import SimpleCalibration


@pytest.fixture
def config():
    return Settings(
        calibration_override_threshold=3,
        calibration_deterministic=True,
        calibration_decay_days=7,
    )


@pytest.fixture
def calibration(config, tmp_path):
    return SimpleCalibration(config, persist_path=tmp_path / "test_calibration.json")


def test_initial_state(calibration):
    assert calibration.get_override_count("nonexistent") == 0
    status = calibration.get_health_status()
    assert status["deterministic"] is True
    assert status["actions_tracked"] == 0
    assert status["override_threshold"] == 3


@pytest.mark.asyncio
async def test_record_override_increments_count(calibration):
    signal = CalibrationSignal(action_hash="hash_abc", outcome="user_denied", user_override=True)
    risk = await calibration.record_override(signal)
    assert calibration.get_override_count("hash_abc") == 1
    assert risk is not None


@pytest.mark.asyncio
async def test_record_override_returns_original_risk_below_threshold(calibration):
    signal = CalibrationSignal(
        action_hash="hash_def",
        risk_features={"visual_divergence": 0.8, "action_is_destructive": 0.7},
        outcome="user_denied",
        user_override=True,
    )
    risk = await calibration.record_override(signal)
    assert risk == RiskLevel.HIGH


@pytest.mark.asyncio
async def test_record_override_returns_demoted_risk_after_threshold(calibration):
    signal = CalibrationSignal(
        action_hash="hash_demote",
        risk_features={"visual_divergence": 0.8, "action_is_destructive": 0.7},
        outcome="user_denied",
        user_override=True,
    )
    risk1 = await calibration.record_override(signal)
    assert risk1 == RiskLevel.HIGH

    signal2 = CalibrationSignal(
        action_hash="hash_demote",
        risk_features={"visual_divergence": 0.4, "action_is_destructive": 0.3},
        outcome="user_denied",
        user_override=True,
    )
    risk2 = await calibration.record_override(signal2)
    assert risk2 == RiskLevel.MEDIUM

    risk3 = await calibration.record_override(signal2)
    assert risk3 == RiskLevel.LOW


@pytest.mark.asyncio
async def test_record_override_empty_action_hash(calibration):
    signal = CalibrationSignal(action_hash="", outcome="user_denied", user_override=True)
    risk = await calibration.record_override(signal)
    assert risk is None


@pytest.mark.asyncio
async def test_reset_for_action(calibration):
    signal = CalibrationSignal(action_hash="hash_reset", outcome="user_denied", user_override=True)
    await calibration.record_override(signal)
    assert calibration.get_override_count("hash_reset") == 1

    calibration.reset_for_action("hash_reset")
    assert calibration.get_override_count("hash_reset") == 0


@pytest.mark.asyncio
async def test_reset_all(calibration):
    for i in range(5):
        signal = CalibrationSignal(action_hash=f"hash_{i}", outcome="user_denied", user_override=True)
        await calibration.record_override(signal)

    assert calibration.get_override_count("hash_0") == 1
    assert calibration.get_override_count("hash_4") == 1

    await calibration.reset_all()
    assert calibration.get_override_count("hash_0") == 0
    assert calibration.get_override_count("hash_4") == 0


def test_demote_risk():
    cal = SimpleCalibration()
    assert cal._demote_risk(RiskLevel.CRITICAL) == RiskLevel.CRITICAL
    assert cal._demote_risk(RiskLevel.HIGH) == RiskLevel.HIGH
    assert cal._demote_risk(RiskLevel.MEDIUM) == RiskLevel.LOW
    assert cal._demote_risk(RiskLevel.LOW) == RiskLevel.SAFE
    assert cal._demote_risk(RiskLevel.SAFE) == RiskLevel.SAFE


def test_critical_never_demoted():
    cal = SimpleCalibration()
    assert cal._demote_risk(RiskLevel.CRITICAL) == RiskLevel.CRITICAL


def test_high_never_demoted():
    cal = SimpleCalibration()
    assert cal._demote_risk(RiskLevel.HIGH) == RiskLevel.HIGH


def test_features_to_risk():
    cal = SimpleCalibration()
    assert cal._features_to_risk({"a": 0.9}) == RiskLevel.CRITICAL
    assert cal._features_to_risk({"a": 0.7}) == RiskLevel.HIGH
    assert cal._features_to_risk({"a": 0.4}) == RiskLevel.MEDIUM
    assert cal._features_to_risk({"a": 0.1}) == RiskLevel.LOW
    assert cal._features_to_risk({}) == RiskLevel.SAFE
    assert cal._features_to_risk({"a": 0.0}) == RiskLevel.SAFE


@pytest.mark.asyncio
async def test_persistence(tmp_path, config):
    path = tmp_path / "persist.json"
    cal = SimpleCalibration(config, persist_path=path)

    signal = CalibrationSignal(action_hash="hash_persist", outcome="user_denied", user_override=True)
    await cal.record_override(signal)
    await cal.flush()

    assert path.exists()
    with open(path) as f:
        data = json.load(f)
    assert "hash_persist" in data
    assert data["hash_persist"]["count"] == 1
    assert "last_override_timestamp" in data["hash_persist"]


@pytest.mark.asyncio
async def test_load_persistence(tmp_path, config):
    path = tmp_path / "load.json"
    with open(path, "w") as f:
        json.dump({"hash_loaded": {"count": 5, "last_override_timestamp": 1000}}, f)

    cal = SimpleCalibration(config, persist_path=path)
    assert cal.get_override_count("hash_loaded") == 5


@pytest.mark.asyncio
async def test_load_legacy_persistence(tmp_path, config):
    path = tmp_path / "legacy.json"
    with open(path, "w") as f:
        json.dump({"hash_legacy": 3}, f)

    cal = SimpleCalibration(config, persist_path=path)
    assert cal.get_override_count("hash_legacy") == 3


def test_default_threshold():
    cal = SimpleCalibration()
    assert cal._threshold == 3


def test_custom_threshold():
    config = Settings(calibration_override_threshold=5, calibration_deterministic=True)
    cal = SimpleCalibration(config)
    assert cal._threshold == 5


def test_get_health_status(calibration):
    status = calibration.get_health_status()
    assert status["enabled"] is True
    assert status["deterministic"] is True
    assert status["override_threshold"] == 3
    assert status["decay_days"] == 7
    assert status["actions_tracked"] == 0


@pytest.mark.asyncio
async def test_decay_disabled_with_zero(tmp_path):
    config = Settings(calibration_decay_days=0, calibration_deterministic=True)
    cal = SimpleCalibration(config, persist_path=tmp_path / "no_decay.json")
    assert cal._decay_seconds == 0

    signal = CalibrationSignal(action_hash="hash_no_decay", outcome="user_denied", user_override=True)
    cal._state["hash_no_decay"] = {"count": 5, "last_override_timestamp": 0}
    await cal.record_override(signal)
    assert cal.get_override_count("hash_no_decay") == 6


@pytest.mark.asyncio
async def test_decay_reduces_count_after_expiry(tmp_path):
    config = Settings(calibration_decay_days=1, calibration_deterministic=True)
    cal = SimpleCalibration(config, persist_path=tmp_path / "decay.json")

    old_time = time.time() - (2 * 86400)
    cal._state["hash_decay"] = {"count": 5, "last_override_timestamp": old_time}

    signal = CalibrationSignal(action_hash="hash_decay", outcome="user_denied", user_override=True)
    await cal.record_override(signal)

    assert cal.get_override_count("hash_decay") < 5


@pytest.mark.asyncio
async def test_decay_multiple_units(tmp_path):
    config = Settings(calibration_decay_days=1, calibration_deterministic=True)
    cal = SimpleCalibration(config, persist_path=tmp_path / "multi_decay.json")

    old_time = time.time() - (5 * 86400)
    cal._state["hash_multi"] = {"count": 10, "last_override_timestamp": old_time}

    signal = CalibrationSignal(action_hash="hash_multi", outcome="user_denied", user_override=True)
    await cal.record_override(signal)

    count = cal.get_override_count("hash_multi")
    assert count <= 6
