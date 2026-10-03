from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Episode:
    episode_id: str
    timestamp: float
    goal: str
    outcome: str
    duration_ms: int = 0
    user_feedback: Optional[str] = None
    model_used: Optional[str] = None


@dataclass
class ActionRecord:
    action_id: str
    episode_id: str
    sequence: int
    action_type: str
    parameters: dict[str, Any]
    outcome: str
    execution_time_ms: int
    error_message: Optional[str] = None


@dataclass
class StateDiff:
    diff_id: str
    action_id: str
    pre_screenshot_hash: Optional[str] = None
    post_screenshot_hash: Optional[str] = None
    visual_divergence: float = 0.0
    text_added: Optional[str] = None
    text_removed: Optional[str] = None
    window_changed: bool = False
