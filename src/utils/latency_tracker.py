import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class StepRecord:
    name: str
    status: str  # ok | fail | skipped
    elapsed_ms: float
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class LatencyTracker:
    def __init__(self, report_dir: str = "data/reports") -> None:
        self._steps: list[StepRecord] = []
        self._start_times: dict[str, float] = {}
        self._session_start: float = time.monotonic()
        self._report_dir = Path(report_dir)
        self._report_dir.mkdir(parents=True, exist_ok=True)

    def start_step(self, name: str) -> None:
        self._start_times[name] = time.monotonic()

    def finish_step(
        self,
        name: str,
        status: str = "ok",
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        start = self._start_times.pop(name, None)
        elapsed_ms = (time.monotonic() - start) * 1000 if start else 0.0
        self._steps.append(
            StepRecord(
                name=name,
                status=status,
                elapsed_ms=round(elapsed_ms, 1),
                error=error,
                metadata=metadata or {},
            )
        )

    @property
    def total_elapsed_ms(self) -> float:
        return round((time.monotonic() - self._session_start) * 1000, 1)

    def to_dict(self) -> dict:
        return {
            "total_elapsed_ms": self.total_elapsed_ms,
            "steps": [asdict(s) for s in self._steps],
        }

    def save_report(self, filename: str = "smoke_report.json") -> Path:
        report = self.to_dict()
        report_path = self._report_dir / filename
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return report_path
