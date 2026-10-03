from typing import List, Optional

from src.governance.models import RiskAssessment, RiskLevel

_RISK_PRIORITY = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}

class RiskRules:
    def __init__(self):
        self.dangerous_keywords = [
            "delete", "remove", "kill", "format", "wipe", "sudo", "rm", "drop table",
            "uninstall", "shutdown", "reboot", "restart",
        ]
        self.financial_keywords = [
            "transfer", "payment", "refund", "purchase", "buy", "checkout",
            "withdraw", "deposit", "pay",
        ]
        self.auth_keywords = [
            "login", "sign in", "signin", "authenticate", "password", "2fa", "mfa",
            "otp", "verification code",
        ]

    def _find_keywords(self, text: str, keywords: List[str]) -> List[str]:
        lower = text.lower()
        return [kw for kw in keywords if kw in lower]

    def assess_action(
        self,
        action_type: str,
        parameters: dict,
        app_context: str = "",
    ) -> RiskAssessment:
        text_params = " ".join(str(v) for k, v in parameters.items() if isinstance(v, (str, int)))
        combined = f"{text_params} {app_context}"

        if action_type == "press_hotkey":
            keys = parameters.get("keys", [])
            if isinstance(keys, tuple):
                keys_str = "+".join(map(str.lower, keys))
            else:
                keys_str = str(keys).lower()

        if action_type == "type_text":
            text = parameters.get("text", "")
            dangerous = self._find_keywords(text, self.dangerous_keywords)
            financial = self._find_keywords(text, self.financial_keywords)
            auth = self._find_keywords(text, self.auth_keywords)

            candidates = []
            if dangerous:
                candidates.append((RiskLevel.CRITICAL, 0.95, [f"dangerous keyword: {dangerous[0]}"], True, "data_loss"))
            if auth:
                candidates.append((RiskLevel.HIGH, 0.8, ["auth-related text"], True, "auth"))
            if financial:
                candidates.append((RiskLevel.MEDIUM, 0.5, ["financial action"], False, "auth"))

            if candidates:
                best = max(candidates, key=lambda c: (_RISK_PRIORITY[c[0]], c[1]))
                return RiskAssessment(
                    risk_level=best[0], score=best[1], reasons=best[2],
                    requires_confirmation=best[3], sensitive_data_detected=False, category=best[4],
                )

        if action_type in ("click", "double_click", "right_click"):
            text = parameters.get("button_text", "").lower() if isinstance(parameters.get("button_text"), str) else ""
            dangerous = self._find_keywords(text, self.dangerous_keywords)
            financial = self._find_keywords(text, self.financial_keywords)
            auth = self._find_keywords(text, self.auth_keywords)

            candidates = []
            if dangerous:
                candidates.append((RiskLevel.HIGH, 0.85, [f"destructive button: {text}"], True, "data_loss"))
            if financial:
                candidates.append((RiskLevel.MEDIUM, 0.6, [f"financial button: {text}"], True, "auth"))
            if auth:
                candidates.append((RiskLevel.MEDIUM, 0.5, [f"auth button: {text}"], False, "auth"))

            if candidates:
                best = max(candidates, key=lambda c: (_RISK_PRIORITY[c[0]], c[1]))
                return RiskAssessment(
                    risk_level=best[0], score=best[1], reasons=best[2],
                    requires_confirmation=best[3], sensitive_data_detected=False, category=best[4],
                )

        if action_type == "screenshot":
            return RiskAssessment(
                risk_level=RiskLevel.MEDIUM,
                score=0.4,
                reasons=["captures screen content"],
                requires_confirmation=False,
                sensitive_data_detected=False,
                category="ui_trap",
            )

        return RiskAssessment(
            risk_level=RiskLevel.SAFE,
            score=0.0,
            reasons=["action is safe"],
            requires_confirmation=False,
            sensitive_data_detected=False,
            category="safe",
        )
