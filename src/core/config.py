import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "DEBUG"
    data_dir: Path = Path("data")
    screen_capture_interval_ms: int = 1000
    tesseract_path: str = "tesseract"
    ocr_language: str = "eng"
    screen_capture_quality: int = 80
    enable_ocr_fallback: bool = True
    action_timeout_ms: int = 5000
    safe_click_margin: int = 10
    mouse_move_duration: float = 0.2
    type_interval: float = 0.05
    enable_compensation: bool = True
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "openrouter/optimus-alpha"
    fallback_model_fast: str = "anthropic/claude-3-haiku"
    fallback_model_accurate: str = "anthropic/claude-3.5-sonnet"
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 3
    enable_llm_cache: bool = True
    llm_cache_ttl_seconds: int = 3600
    privacy_mode: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: float = 30.0
    require_confirm_high_risk: bool = True
    require_confirm_medium_risk: bool = False
    enable_policy_engine: bool = True
    sensitive_detection_enabled: bool = True
    health_check_interval_seconds: int = 30
    metrics_flush_interval_seconds: int = 60
    task_queue_max_size: int = 100
    calibration_enabled: bool = True
    calibration_alpha: float = 0.1
    calibration_learning_rate: float = 0.05
    calibration_override_threshold: int = 3
    calibration_deterministic: bool = True
    calibration_decay_days: int = 7
    uia_click_debounce_ms: int = 80
    uia_enable_visual_stability_check: bool = True
    max_daily_llm_budget: float = 2.0
    llm_request_timeout_seconds: float = 2.0
    context_lock_timeout_ms: int = 5000

    @property
    def openrouter_enabled(self) -> bool:
        return bool(self.openrouter_api_key) and not self.privacy_mode


_settings: Settings | None = None


def clear_settings_cache() -> None:
    global _settings
    _settings = None


def load_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    load_dotenv()

    config_data: dict = {}
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            loaded = yaml.safe_load(f)
            if loaded:
                config_data = loaded

    env_map = {
        "ENVIRONMENT": ("environment", str),
        "LOG_LEVEL": ("log_level", str),
        "DATA_DIR": ("data_dir", str),
        "SCREEN_CAPTURE_INTERVAL_MS": ("screen_capture_interval_ms", int),
        "TESSERACT_PATH": ("tesseract_path", str),
        "OCR_LANGUAGE": ("ocr_language", str),
        "SCREEN_CAPTURE_QUALITY": ("screen_capture_quality", int),
        "ENABLE_OCR_FALLBACK": ("enable_ocr_fallback", bool),
        "ACTION_TIMEOUT_MS": ("action_timeout_ms", int),
        "SAFE_CLICK_MARGIN": ("safe_click_margin", int),
        "MOUSE_MOVE_DURATION": ("mouse_move_duration", float),
        "TYPE_INTERVAL": ("type_interval", float),
        "ENABLE_COMPENSATION": ("enable_compensation", bool),
        "OPENROUTER_API_KEY": ("openrouter_api_key", str),
        "OPENROUTER_BASE_URL": ("openrouter_base_url", str),
        "DEFAULT_MODEL": ("default_model", str),
        "FALLBACK_MODEL_FAST": ("fallback_model_fast", str),
        "FALLBACK_MODEL_ACCURATE": ("fallback_model_accurate", str),
        "LLM_TIMEOUT_SECONDS": ("llm_timeout_seconds", int),
        "LLM_MAX_RETRIES": ("llm_max_retries", int),
        "ENABLE_LLM_CACHE": ("enable_llm_cache", bool),
        "LLM_CACHE_TTL_SECONDS": ("llm_cache_ttl_seconds", int),
        "REQUIRE_CONFIRM_HIGH_RISK": ("require_confirm_high_risk", bool),
        "REQUIRE_CONFIRM_MEDIUM_RISK": ("require_confirm_medium_risk", bool),
        "ENABLE_POLICY_ENGINE": ("enable_policy_engine", bool),
        "SENSITIVE_DETECTION_ENABLED": ("sensitive_detection_enabled", bool),
        "HEALTH_CHECK_INTERVAL_SECONDS": ("health_check_interval_seconds", int),
        "METRICS_FLUSH_INTERVAL_SECONDS": ("metrics_flush_interval_seconds", int),
        "TASK_QUEUE_MAX_SIZE": ("task_queue_max_size", int),
        "CALIBRATION_ENABLED": ("calibration_enabled", bool),
        "CALIBRATION_ALPHA": ("calibration_alpha", float),
        "CALIBRATION_LEARNING_RATE": ("calibration_learning_rate", float),
        "CALIBRATION_OVERRIDE_THRESHOLD": ("calibration_override_threshold", int),
        "CALIBRATION_DETERMINISTIC": ("calibration_deterministic", bool),
        "CALIBRATION_DECAY_DAYS": ("calibration_decay_days", int),
        "UIA_CLICK_DEBOUNCE_MS": ("uia_click_debounce_ms", int),
        "UIA_ENABLE_VISUAL_STABILITY_CHECK": ("uia_enable_visual_stability_check", bool),
        "MAX_DAILY_LLM_BUDGET": ("max_daily_llm_budget", float),
        "LLM_REQUEST_TIMEOUT_SECONDS": ("llm_request_timeout_seconds", float),
        "CONTEXT_LOCK_TIMEOUT_MS": ("context_lock_timeout_ms", int),
        "PRIVACY_MODE": ("privacy_mode", bool),
        "OLLAMA_BASE_URL": ("ollama_base_url", str),
        "OLLAMA_MODEL": ("ollama_model", str),
        "OLLAMA_TIMEOUT": ("ollama_timeout", float),
    }

    env_data: dict = {}
    for env_key, (attr_key, type_) in env_map.items():
        if env_key in os.environ:
            raw = os.environ[env_key]
            if type_ == bool:
                value = raw.lower() in ("true", "1", "yes")
            elif type_ == float:
                value = float(raw)
            elif type_ == int:
                value = int(raw)
            else:
                value = raw
            env_data[attr_key] = value

    merged = {**config_data, **env_data}
    _settings = Settings(**merged)
    return _settings
