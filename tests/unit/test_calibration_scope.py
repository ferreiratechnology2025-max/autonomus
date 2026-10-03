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
        calibration_decay_days=0,
    )


@pytest.fixture
def calibration(config, tmp_path):
    return SimpleCalibration(config, persist_path=tmp_path / "scope_test.json")


def test_get_effective_risk_default(calibration):
    risk = calibration.get_effective_risk("delete", "HIGH", {"process_name": "notepad.exe"})
    assert risk == "HIGH"


def test_get_effective_risk_demotes_medium(calibration):
    risk = calibration.get_effective_risk("save", "MEDIUM", {"process_name": "notepad.exe"})
    assert risk == "MEDIUM"


@pytest.mark.asyncio
async def test_calibration_scoped_by_process(calibration):
    cal = calibration

    for _ in range(3):
        signal = CalibrationSignal(
            action_hash="delete:outlook.exe",
            risk_features={"action_is_destructive": 0.6},
            outcome="user_denied",
            user_override=True,
        )
        await cal.record_override(signal)

    risk_outlook = cal.get_effective_risk("delete", "HIGH", {"process_name": "outlook.exe"})
    assert risk_outlook == "HIGH"

    risk_cmd = cal.get_effective_risk("delete", "HIGH", {"process_name": "cmd.exe"})
    assert risk_cmd == "HIGH"

    cal._state["delete:cmd.exe"] = {"count": 5, "last_override_timestamp": 0}
    risk_cmd_low = cal.get_effective_risk("delete", "LOW", {"process_name": "cmd.exe"})
    assert risk_cmd_low == "SAFE"


@pytest.mark.asyncio
async def test_override_one_process_does_not_affect_another(calibration):
    cal = calibration

    signal_outlook = CalibrationSignal(
        action_hash="type_text:outlook.exe",
        risk_features={"action_is_destructive": 0.3},
        outcome="user_denied",
        user_override=True,
    )
    for _ in range(3):
        await cal.record_override(signal_outlook)

    count_outlook = cal.get_override_count("type_text:outlook.exe")
    count_cmd = cal.get_override_count("type_text:cmd.exe")
    assert count_outlook == 3
    assert count_cmd == 0


@pytest.mark.asyncio
async def test_same_action_different_processes_independent(calibration):
    cal = calibration

    for i in range(3):
        await cal.record_override(CalibrationSignal(
            action_hash=f"click:chrome.exe",
            risk_features={"action_is_destructive": 0.4},
            outcome="user_denied",
            user_override=True,
        ))

    await cal.record_override(CalibrationSignal(
        action_hash=f"click:notepad.exe",
        risk_features={"action_is_destructive": 0.4},
        outcome="user_denied",
        user_override=True,
    ))

    assert cal.get_override_count("click:chrome.exe") == 3
    assert cal.get_override_count("click:notepad.exe") == 1
