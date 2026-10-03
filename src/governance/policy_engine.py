import time
from typing import List, Optional, TYPE_CHECKING

from loguru import logger

from src.core.config import Settings
from src.governance.models import PolicyDecision, PolicyOverride, RiskAssessment, RiskLevel
from src.governance.risk_rules import RiskRules
from src.governance.sensitive_detector import SensitiveDataDetector

if TYPE_CHECKING:
    from src.governance.calibration_loop import CalibrationLoop
    from src.governance.calibration_models import CalibrationSignal
    from src.governance.simple_calibration import SimpleCalibration


def _get_foreground_process() -> str:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
        if handle:
            exe_name = ctypes.create_unicode_buffer(260)
            kernel32.GetModuleBaseNameW(handle, None, exe_name, 260)
            kernel32.CloseHandle(handle)
            return exe_name.value.lower()
        return "unknown"
    except Exception as e:
        logger.warning(f"_get_foreground_process falhou: {e}")
        return "unknown"


class PolicyEngine:
    def __init__(
        self,
        config: Settings,
        sensitive_detector: Optional[SensitiveDataDetector] = None,
        risk_rules: Optional[RiskRules] = None,
    ) -> None:
        self.config = config
        self.sensitive_detector = sensitive_detector or SensitiveDataDetector()
        self.risk_rules = risk_rules or RiskRules()
        self.override_history: List[PolicyOverride] = []
        self.simple_calibration: Optional["SimpleCalibration"] = None

    async def evaluate_action(
        self,
        action_type: str,
        parameters: dict,
        context: dict,
    ) -> PolicyDecision:
        if not self.config.enable_policy_engine:
            return PolicyDecision.ALLOW

        sensitive = self._detect_sensitive_in_params(parameters)
        assessment = self.risk_rules.assess_action(
            action_type, parameters, context.get("app", ""),
        )

        if sensitive:
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.score = 1.0
            assessment.sensitive_data_detected = True
            assessment.reasons.append("sensitive data detected in parameters")

        decision = self._map_to_decision(assessment)

        logger.info(
            f"Policy {decision.value.upper()} "
            f"{action_type} "
            f"(risk={assessment.risk_level.value}, "
            f"score={assessment.score:.2f}, "
            f"category={assessment.category})"
        )
        return decision

    def _detect_sensitive_in_params(self, parameters: dict) -> bool:
        for value in parameters.values():
            if isinstance(value, str):
                if self.sensitive_detector.has_sensitive_data(value):
                    return True
        return False

    def _map_to_decision(self, assessment: RiskAssessment) -> PolicyDecision:
        if assessment.risk_level == RiskLevel.CRITICAL:
            return PolicyDecision.BLOCK
        elif assessment.risk_level == RiskLevel.HIGH:
            if self.config.require_confirm_high_risk:
                return PolicyDecision.CONFIRM
            return PolicyDecision.ALLOW
        elif assessment.risk_level == RiskLevel.MEDIUM:
            if self.config.require_confirm_medium_risk:
                return PolicyDecision.CONFIRM
            return PolicyDecision.ALLOW
        return PolicyDecision.ALLOW

    def record_override(
        self,
        user_id: str,
        action_id: str,
        decision: PolicyDecision,
        reason: str,
    ) -> None:
        override = PolicyOverride(
            user_id=user_id,
            action_id=action_id,
            decision=decision,
            reason=reason,
            timestamp=time.time(),
        )
        self.override_history.append(override)
        logger.info(f"Override recorded: user={user_id} action={action_id} decision={decision.value}")

    async def should_route_to_private_model(
        self,
        prompt: str,
        screenshot: Optional[bytes] = None,
    ) -> bool:
        if self.sensitive_detector.has_sensitive_data(prompt):
            logger.info("Routing to private model: sensitive data in prompt")
            return True
        if screenshot:
            image_results = await self.sensitive_detector.detect_in_image(screenshot)
            if image_results:
                logger.info(f"Routing to private model: sensitive data in screenshot ({len(image_results)} hits)")
                return True
        return False

    async def evaluate_action_with_calibration(
        self,
        action_type: str,
        parameters: dict,
        context: dict,
    ) -> tuple[PolicyDecision, "CalibrationSignal"]:
        from src.governance.calibration_models import CalibrationSignal

        decision = await self.evaluate_action(action_type, parameters, context)
        features = self._extract_features(action_type, parameters, context)

        process_name = context.get("process_name") or _get_foreground_process()
        action_hash = str(hash(f"{action_type}{parameters}{process_name}"))
        signal = CalibrationSignal(
            action_hash=action_hash,
            risk_features=features,
            outcome="pending",
            user_override=False,
        )

        if self.config.calibration_deterministic and self.simple_calibration is not None:
            override_count = self.simple_calibration.get_override_count(signal.action_hash)
            if override_count >= self.config.calibration_override_threshold:
                demoted = self.simple_calibration._features_to_risk(features)
                logger.info(
                    f"Calibration override threshold reached for {signal.action_hash}: "
                    f"demoting risk based on {override_count} overrides"
                )
                decision = self._map_to_decision(
                    RiskAssessment(
                        risk_level=demoted,
                        score=0.0,
                        reasons=["risk demoted by calibration"],
                        requires_confirmation=False,
                        sensitive_data_detected=False,
                        category="calibrated",
                    )
                )

        return decision, signal

    def _extract_features(self, action_type: str, parameters: dict, context: dict) -> dict:
        return {
            "visual_divergence": 0.0,
            "historical_fail_rate": 0.0,
            "compensation_available": -0.15 if self.config.enable_compensation else 0.0,
            "sensitive_data_detected": 0.5 if self._detect_sensitive_in_params(parameters) else 0.0,
            "action_is_destructive": 0.4 if action_type == "type_text" and any(
                kw in str(parameters.get("text", "")).lower()
                for kw in ["delete", "remove", "kill", "format", "wipe"]
            ) else 0.0,
            "window_changed": 0.0,
        }

    async def update_with_feedback(self, signal: "CalibrationSignal") -> None:
        if self.config.calibration_deterministic and self.simple_calibration is not None:
            if signal.user_override:
                await self.simple_calibration.record_override(signal)
        elif hasattr(self, "calibration_loop") and self.calibration_loop:
            await self.calibration_loop.record_feedback(signal)

    def get_health_status(self) -> dict:
        status = {
            "enabled": self.config.enable_policy_engine,
            "sensitive_detection": self.config.sensitive_detection_enabled,
            "require_confirm_high_risk": self.config.require_confirm_high_risk,
            "require_confirm_medium_risk": self.config.require_confirm_medium_risk,
            "overrides_logged": len(self.override_history),
        }
        if self.config.calibration_deterministic and self.simple_calibration is not None:
            status["simple_calibration"] = self.simple_calibration.get_health_status()
        return status
