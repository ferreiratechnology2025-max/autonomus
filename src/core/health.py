from pathlib import Path

from src.core.config import Settings


class HealthChecker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def check_storage(self) -> dict:
        data_dir = self._settings.data_dir
        path = Path(data_dir)
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            return {"status": "healthy", "details": {"path": str(data_dir)}}
        except OSError:
            return {"status": "unhealthy", "details": {"path": str(data_dir), "error": "not writable"}}

    def check_config(self) -> dict:
        return {
            "status": "healthy",
            "details": {
                "environment": self._settings.environment,
                "log_level": self._settings.log_level,
            },
        }

    def check_screen_capture(self) -> dict:
        try:
            from src.perception.screen_capture import ScreenCapture

            capture = ScreenCapture(monitor=1)
            size = capture.get_screen_size()
            return {
                "status": "healthy",
                "details": {"screen_size": f"{size[0]}x{size[1]}"},
            }
        except Exception as e:
            return {"status": "degraded", "details": {"error": str(e)}}

    def check_ocr(self) -> dict:
        try:
            from src.perception.ocr import OCRProcessor

            ocr = OCRProcessor(self._settings)
            if ocr._available:
                return {"status": "healthy", "details": {"tesseract_path": self._settings.tesseract_path}}
            return {"status": "degraded", "details": {"tesseract_path": self._settings.tesseract_path, "note": "tesseract not available"}}
        except Exception as e:
            return {"status": "degraded", "details": {"error": str(e)}}

    def check_database(self) -> dict:
        try:
            db_dir = Path(self._settings.data_dir) / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            return {"status": "healthy", "details": {"path": str(db_dir)}}
        except Exception as e:
            return {"status": "degraded", "details": {"error": str(e)}}

    def check_policy(self) -> dict:
        try:
            from src.governance.policy_engine import PolicyEngine

            engine = PolicyEngine(self._settings)
            status = engine.get_health_status()
            return {
                "status": "healthy" if status["enabled"] else "degraded",
                "details": status,
            }
        except Exception as e:
            return {"status": "degraded", "details": {"error": str(e)}}

    def check_calibration(self) -> dict:
        try:
            from src.governance.calibration_loop import CalibrationLoop
            from src.governance.policy_engine import PolicyEngine

            policy = PolicyEngine(self._settings)
            cal = CalibrationLoop(policy, config=self._settings)
            return {"status": "healthy", "details": cal.get_health_status()}
        except Exception as e:
            return {"status": "degraded", "details": {"error": str(e)}}

    def check_llm(self) -> dict:
        ollama = self._settings.ollama_base_url
        api_key = self._settings.openrouter_api_key
        if self._settings.privacy_mode:
            return {
                "status": "healthy",
                "details": {"mode": "privacy", "ollama": ollama, "model": self._settings.ollama_model},
            }
        if not api_key and not self._settings.ollama_base_url:
            return {"status": "degraded", "details": {"note": "No LLM backend configured"}}
        return {
            "status": "healthy",
            "details": {
                "openrouter": bool(api_key),
                "ollama": ollama,
                "model": self._settings.ollama_model,
            },
        }

    def get_status(self) -> dict:
        storage = self.check_storage()
        config = self.check_config()
        screen = self.check_screen_capture()
        ocr = self.check_ocr()
        database = self.check_database()
        llm = self.check_llm()
        policy = self.check_policy()
        calibration = self.check_calibration()

        checks = {
            "storage": storage,
            "config": config,
            "screen_capture": screen,
            "ocr": ocr,
            "database": database,
            "llm": llm,
            "policy": policy,
            "calibration": calibration,
        }

        all_healthy = all(c["status"] == "healthy" for c in checks.values())
        any_unhealthy = any(c["status"] == "unhealthy" for c in checks.values())

        if all_healthy:
            overall = "healthy"
        elif any_unhealthy:
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {"status": overall, "checks": checks}
