import os
from pathlib import Path

import pytest
import yaml

from src.core.config import Settings, clear_settings_cache, load_settings


@pytest.fixture(autouse=True)
def reset_settings():
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_load_settings_returns_settings_instance():
    settings = load_settings()
    assert isinstance(settings, Settings)


def test_settings_has_default_values():
    settings = Settings()
    assert settings.environment == "development"
    assert settings.log_level == "DEBUG"
    assert settings.screen_capture_interval_ms == 1000


def test_settings_data_dir_defaults_to_data():
    settings = Settings()
    assert settings.data_dir == Path("data")


def test_environment_variable_overrides_default(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    settings = load_settings()
    assert settings.environment == "production"


def test_log_level_env_var(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    settings = load_settings()
    assert settings.log_level == "WARNING"


def test_screen_capture_interval_env_var(monkeypatch):
    monkeypatch.setenv("SCREEN_CAPTURE_INTERVAL_MS", "500")
    settings = load_settings()
    assert settings.screen_capture_interval_ms == 500


def test_load_settings_is_singleton():
    s1 = load_settings()
    s2 = load_settings()
    assert s1 is s2


def test_yaml_config_loading(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({"log_level": "ERROR"}))

    monkeypatch.chdir(tmp_path)

    settings = load_settings()
    assert settings.log_level == "ERROR"


def test_env_var_overrides_yaml(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({"log_level": "ERROR"}))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")

    settings = load_settings()
    assert settings.log_level == "CRITICAL"
