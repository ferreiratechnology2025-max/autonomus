import json
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from src.core.config import Settings
from src.governance.calibration_models import CalibrationSignal
from src.governance.policy_engine import PolicyEngine
from src.memory.memory import MemorySystem


class CalibrationLoop:
    def __init__(
        self,
        policy_engine: PolicyEngine,
        memory: Optional[MemorySystem] = None,
        config: Optional[Settings] = None,
    ) -> None:
        self.policy = policy_engine
        self.memory = memory
        self.alpha = config.calibration_alpha if config else 0.1
        self.lr = config.calibration_learning_rate if config else 0.05
        self.weights = self._load_weights()
        self.predicted_risk_ema = 0.5
        self._weights_path = Path("data/calibration_weights.json")

    async def record_feedback(self, signal: CalibrationSignal) -> None:
        if not signal.risk_features:
            logger.debug("No risk features in signal, skipping calibration")
            return

        if signal.outcome in ("success", "user_approved"):
            target = 0.0
        elif signal.outcome in ("failed", "user_denied", "rollback"):
            target = 1.0
        else:
            return

        pred = sum(self.weights.get(f, 0.0) * v for f, v in signal.risk_features.items())
        pred = max(0.0, min(1.0, pred))

        self.predicted_risk_ema = self.alpha * pred + (1 - self.alpha) * self.predicted_risk_ema

        error = target - self.predicted_risk_ema
        for feature, value in signal.risk_features.items():
            current = self.weights.get(feature, 0.1)
            self.weights[feature] = max(0.0, min(1.0, current + self.lr * error * value))

        await self._save_weights()

        logger.debug(
            f"Calibration: outcome={signal.outcome} "
            f"target={target:.2f} pred={pred:.2f} ema={self.predicted_risk_ema:.2f} "
            f"error={error:.3f}"
        )

    async def get_weights(self) -> Dict[str, float]:
        return self.weights.copy()

    async def reset_weights(self) -> None:
        self.weights = self._default_weights()
        await self._save_weights()
        logger.warning("CalibrationLoop: weights reset to defaults")

    def _default_weights(self) -> Dict[str, float]:
        return {
            "visual_divergence": 0.3,
            "historical_fail_rate": 0.25,
            "compensation_available": -0.15,
            "sensitive_data_detected": 0.5,
            "action_is_destructive": 0.4,
            "window_changed": 0.2,
        }

    def _load_weights(self) -> Dict[str, float]:
        try:
            path = Path(self._weights_path)
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load calibration weights: {e}")
        return self._default_weights()

    async def _save_weights(self) -> None:
        try:
            path = Path(self._weights_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.weights, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save calibration weights: {e}")

    def get_health_status(self) -> dict:
        return {
            "enabled": True,
            "weights_count": len(self.weights),
            "risk_ema": round(self.predicted_risk_ema, 3),
        }
