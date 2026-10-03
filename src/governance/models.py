from dataclasses import dataclass
from enum import Enum
from typing import List


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecision(Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    BLOCK = "block"
    SANDBOX = "sandbox"


@dataclass
class RiskAssessment:
    risk_level: RiskLevel
    score: float
    reasons: List[str]
    requires_confirmation: bool
    sensitive_data_detected: bool
    category: str


@dataclass
class PolicyOverride:
    user_id: str
    action_id: str
    decision: PolicyDecision
    reason: str
    timestamp: float
