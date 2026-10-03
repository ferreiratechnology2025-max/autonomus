import json
import time
from pathlib import Path
from typing import Optional

from loguru import logger


class CostBudget:
    def __init__(self, max_daily_budget: float = 2.0, persist_path: Optional[Path] = None) -> None:
        self._max_daily = max_daily_budget
        self._persist_path = persist_path or Path("data/llm_budget.json")
        self._today_key: str = ""
        self._today_spend: float = 0.0
        self._load()

    def record_cost(self, cost_usd: float) -> bool:
        if cost_usd <= 0:
            return True
        self._ensure_today()
        new_total = self._today_spend + cost_usd
        if new_total > self._max_daily:
            logger.warning(
                f"Daily LLM budget would be exceeded: ${self._today_spend:.4f} + ${cost_usd:.6f} = "
                f"${new_total:.4f} > ${self._max_daily:.2f} cap. Call rejected."
            )
            return False
        self._today_spend = new_total
        self._save()
        logger.debug(f"Budget: spent ${cost_usd:.6f}, daily total ${self._today_spend:.4f}/${self._max_daily:.2f}")
        return True

    def budget_remaining(self) -> float:
        self._ensure_today()
        return max(0.0, self._max_daily - self._today_spend)

    def is_exhausted(self) -> bool:
        self._ensure_today()
        return self._today_spend >= self._max_daily

    def reset_today(self) -> None:
        self._today_key = time.strftime("%Y-%m-%d")
        self._today_spend = 0.0
        self._save()

    def get_health_status(self) -> dict:
        self._ensure_today()
        return {
            "max_daily_budget": self._max_daily,
            "today_spend": round(self._today_spend, 6),
            "budget_remaining": round(self.budget_remaining(), 6),
            "exhausted": self.is_exhausted(),
        }

    def _ensure_today(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self._today_key != today:
            self._today_key = today
            self._today_spend = 0.0

    def _load(self) -> None:
        try:
            if self._persist_path.exists():
                with open(self._persist_path) as f:
                    data = json.load(f)
                saved_date = data.get("date", "")
                self._today_key = time.strftime("%Y-%m-%d")
                if saved_date == self._today_key:
                    self._today_spend = float(data.get("spend", 0.0))
                else:
                    self._today_spend = 0.0
                logger.debug(f"Budget loaded: date={saved_date} spend={self._today_spend}")
        except Exception as e:
            logger.warning(f"Failed to load budget state: {e}")

    def _save(self) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "w") as f:
                json.dump({"date": self._today_key, "spend": self._today_spend}, f)
        except Exception as e:
            logger.error(f"Failed to save budget state: {e}")
