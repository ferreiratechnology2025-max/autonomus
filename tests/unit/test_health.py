from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config import Settings
from src.core.health import HealthChecker


@pytest.fixture
def settings():
    return Settings(data_dir=Path("data"))


@pytest.fixture
def health_checker(settings):
    return HealthChecker(settings)


def test_check_storage_healthy_when_dir_exists(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    settings = Settings(data_dir=data_dir)
    checker = HealthChecker(settings)
    result = checker.check_storage()
    assert result["status"] == "healthy"


def test_check_storage_creates_missing_dir(tmp_path):
    data_dir = tmp_path / "new_data"
    settings = Settings(data_dir=data_dir)
    checker = HealthChecker(settings)
    result = checker.check_storage()
    assert result["status"] == "healthy"
    assert data_dir.exists()


def test_check_config_healthy_with_valid_settings(health_checker):
    result = health_checker.check_config()
    assert result["status"] == "healthy"
    assert "environment" in result["details"]


def test_check_screen_capture_healthy(health_checker):
    with patch("src.perception.screen_capture.ScreenCapture") as mock_sc:
        mock_sc.return_value.get_screen_size.return_value = (1920, 1080)
        result = health_checker.check_screen_capture()
    assert result["status"] == "healthy"
    assert result["details"]["screen_size"] == "1920x1080"


def test_check_screen_capture_degraded(health_checker):
    with patch("src.perception.screen_capture.ScreenCapture") as mock_sc:
        mock_sc.return_value.get_screen_size.side_effect = Exception("no display")
        result = health_checker.check_screen_capture()
    assert result["status"] == "degraded"


def test_check_ocr_healthy(health_checker):
    with patch("src.perception.ocr.OCRProcessor") as mock_ocr:
        mock_ocr.return_value._available = True
        result = health_checker.check_ocr()
    assert result["status"] == "healthy"


def test_check_ocr_degraded(health_checker):
    with patch("src.perception.ocr.OCRProcessor") as mock_ocr:
        mock_ocr.return_value._available = False
        result = health_checker.check_ocr()
    assert result["status"] == "degraded"


def test_check_database_healthy(health_checker, tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    checker = HealthChecker(settings)
    result = checker.check_database()
    assert result["status"] == "healthy"


def test_check_llm_healthy():
    settings = Settings(openrouter_api_key="sk-or-v1-test-key")
    checker = HealthChecker(settings)
    result = checker.check_llm()
    assert result["status"] == "healthy"
    assert result["details"]["openrouter"] is True
    assert result["details"]["ollama"] == "http://localhost:11434"


def test_check_llm_healthy_with_ollama_only(health_checker):
    result = health_checker.check_llm()
    assert result["status"] == "healthy"
    assert result["details"]["openrouter"] is False
    assert result["details"]["ollama"] == "http://localhost:11434"


def test_get_status_returns_dict(health_checker):
    status = health_checker.get_status()
    assert isinstance(status, dict)
    assert "status" in status
    assert "checks" in status


def test_get_status_includes_all_checks(health_checker):
    with (
        patch.object(health_checker, "check_screen_capture") as mock_sc,
        patch.object(health_checker, "check_ocr") as mock_ocr,
        patch.object(health_checker, "check_database") as mock_db,
        patch.object(health_checker, "check_llm") as mock_llm,
        patch.object(health_checker, "check_policy") as mock_policy,
        patch.object(health_checker, "check_calibration") as mock_cal,
    ):
        mock_sc.return_value = {"status": "healthy", "details": {}}
        mock_ocr.return_value = {"status": "healthy", "details": {}}
        mock_db.return_value = {"status": "healthy", "details": {}}
        mock_llm.return_value = {"status": "healthy", "details": {}}
        mock_policy.return_value = {"status": "healthy", "details": {}}
        mock_cal.return_value = {"status": "healthy", "details": {}}
        status = health_checker.get_status()
    assert "screen_capture" in status["checks"]
    assert "ocr" in status["checks"]
    assert "database" in status["checks"]
    assert "llm" in status["checks"]
    assert "policy" in status["checks"]
    assert "calibration" in status["checks"]
