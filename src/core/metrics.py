import threading
from typing import Dict


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "llm_timeout_count": 0,
            "llm_request_count": 0,
            "llm_cache_hit_count": 0,
            "llm_budget_exhausted_count": 0,
            "context_lock_pid_fallback": 0,
            "context_lock_lost": 0,
            "visual_stability_false_positives": 0,
            "click_element_total": 0,
            "pid_fallback_triggered": 0,
        }

    def increment(self, key: str, delta: int = 1) -> None:
        with self._lock:
            if key in self._counters:
                self._counters[key] += delta

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            for k in self._counters:
                self._counters[k] = 0


_metrics: RuntimeMetrics | None = None


def get_metrics() -> RuntimeMetrics:
    global _metrics
    if _metrics is None:
        _metrics = RuntimeMetrics()
    return _metrics
