import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from uuid import uuid4


@dataclass
class CalibrationSignal:
    signal_id: str = field(default_factory=lambda: uuid4().hex[:8])
    timestamp: float = field(default_factory=time.time)
    action_hash: str = ""
    risk_features: Dict[str, float] = field(default_factory=dict)
    outcome: str = "pending"
    user_override: bool = False
    post_diff: Optional[dict] = None
    skill_id: Optional[str] = None
    episode_id: Optional[str] = None
