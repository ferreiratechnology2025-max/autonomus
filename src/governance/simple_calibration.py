import asyncio
import copy
import json
import time
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from src.core.config import Settings
from src.governance.calibration_models import CalibrationSignal
from src.governance.models import RiskLevel


class SimpleCalibration:
    def __init__(
        self,
        config: Optional[Settings] = None,
        persist_path: Optional[Path] = None,
    ) -> None:
        self._threshold = config.calibration_override_threshold if config else 3
        self._decay_seconds = (config.calibration_decay_days if config else 7) * 86400
        self._state: Dict[str, dict] = {}
        self._persist_path = persist_path or Path("data/simple_calibration.json")
        self._dirty = False
        self._flush_interval = 300.0
        self._flush_task: Optional[asyncio.Task] = None
        self._load()

    async def start_periodic_flush(self) -> None:
        if self._flush_task is not None:
            return
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop_periodic_flush(self) -> None:
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except (asyncio.CancelledError, Exception):
                pass
            self._flush_task = None
        await self._shutdown_flush()

    async def flush(self) -> None:
        if not self._dirty:
            return
        snapshot = copy.deepcopy(self._state)
        safe_path = copy.copy(self._persist_path)
        await asyncio.to_thread(self._save_sync, snapshot, safe_path)
        self._dirty = False

    async def _shutdown_flush(self) -> None:
        try:
            await self.flush()
        except Exception as e:
            logger.critical(f"Shutdown flush failed (data may be stale): {e}")

    async def _periodic_flush(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._flush_interval)
                if self._dirty:
                    await self.flush()
        except asyncio.CancelledError:
            pass

    async def record_override(self, signal: CalibrationSignal) -> Optional[RiskLevel]:
        action_hash = signal.action_hash
        if not action_hash:
            return None

        now = time.time()
        state = self._state.get(action_hash, {"count": 0, "last_override_timestamp": 0})

        if self._decay_seconds > 0 and state["last_override_timestamp"] > 0:
            elapsed = now - state["last_override_timestamp"]
            if elapsed > self._decay_seconds:
                decay_units = max(1, int(elapsed // self._decay_seconds))
                old_count = state["count"]
                state["count"] = max(0, state["count"] - decay_units)
                logger.info(
                    f"Action {action_hash} decayed from {old_count} to {state['count']} "
                    f"({elapsed:.0f}s since last override)"
                )

        state["count"] += 1
        state["last_override_timestamp"] = now
        self._state[action_hash] = state

        self._dirty = True

        original_risk = self._features_to_risk(signal.risk_features)
        if state["count"] >= self._threshold:
            new_level = self._demote_risk(original_risk)
            state["demoted_at"] = now
            state["demoted_to"] = new_level.value
            self._state[action_hash] = state
            logger.info(
                f"Action {action_hash} demoted from {original_risk.value} "
                f"to {new_level.value} after {state['count']} overrides"
            )
            result = new_level
        else:
            result = original_risk

        if result in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            logger.debug(f"Immediate flush for {result.value} override on {action_hash}")
            await self.flush()

        return result

    def get_override_count(self, action_hash: str) -> int:
        state = self._state.get(action_hash, {})
        return state.get("count", 0)

    def reset_for_action(self, action_hash: str) -> None:
        self._state.pop(action_hash, None)
        self._dirty = True

    async def reset_all(self) -> None:
        self._state.clear()
        self._dirty = True
        await self.flush()
        logger.warning("SimpleCalibration: all override counts reset")

    def get_effective_risk(self, action_type: str, base_risk: str, context: dict = None) -> str:
        process_name = context.get("process_name", "unknown") if context else "unknown"
        key = f"{action_type}:{process_name}"
        state = self._state.get(key, {})
        count = state.get("count", 0)
        risk_lower = base_risk.lower()
        if count >= self._threshold and risk_lower in ("medium", "low"):
            demoted = self._demote_risk(RiskLevel(risk_lower))
            return demoted.value.upper()
        return base_risk

    def get_health_status(self) -> dict:
        return {
            "enabled": True,
            "deterministic": True,
            "override_threshold": self._threshold,
            "decay_days": self._decay_seconds // 86400 if self._decay_seconds > 0 else 0,
            "actions_tracked": len(self._state),
            "dirty": self._dirty,
        }

    def _demote_risk(self, risk: RiskLevel) -> RiskLevel:
        mapping = {
            RiskLevel.MEDIUM: RiskLevel.LOW,
            RiskLevel.LOW: RiskLevel.SAFE,
        }
        return mapping.get(risk, risk)

    def _features_to_risk(self, features: Dict[str, float]) -> RiskLevel:
        score = sum(features.values()) / max(len(features), 1)
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.3:
            return RiskLevel.MEDIUM
        elif score > 0.0:
            return RiskLevel.LOW
        return RiskLevel.SAFE

    def _load(self) -> None:
        try:
            if self._persist_path.exists():
                with open(self._persist_path) as f:
                    data = json.load(f)
                    if isinstance(data, dict) and any(isinstance(v, dict) for v in data.values()):
                        self._state = data
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, (int, float)):
                                self._state[k] = {"count": int(v), "last_override_timestamp": 0}
                            else:
                                self._state[k] = v
                logger.debug(f"Loaded {len(self._state)} override states")
        except Exception as e:
            logger.warning(f"Failed to load override states: {e}")

    def _save_sync(self, data: dict, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save override states: {e}")
