import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from uuid import uuid4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    REPAIRING = "repairing"


class RepairStrategy(Enum):
    RETRY = "retry"
    ALTERNATIVE = "alternative"
    ESCALATE_LLM = "escalate_llm"
    ASK_USER = "ask_user"
    ABORT = "abort"


@dataclass
class Task:
    task_id: str = field(default_factory=lambda: uuid4().hex[:8])
    name: str = ""
    description: str = ""
    action_type: Optional[str] = None
    parameters: dict = field(default_factory=dict)
    subtasks: List["Task"] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    precondition: Optional[str] = None
    postcondition: Optional[str] = None


@dataclass
class Plan:
    plan_id: str = field(default_factory=lambda: uuid4().hex[:8])
    goal: str = ""
    root_task: Optional[Task] = None
    created_at: float = field(default_factory=time.time)
    status: TaskStatus = TaskStatus.PENDING
    execution_history: List[dict] = field(default_factory=list)
