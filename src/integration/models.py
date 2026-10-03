from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMRequest:
    prompt: str
    system_prompt: Optional[str] = None
    images: Optional[list[bytes]] = None
    temperature: float = 0.2
    max_tokens: int = 4096
    model: Optional[str] = None


@dataclass
class LLMResponse:
    content: str
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    cached: bool = False
