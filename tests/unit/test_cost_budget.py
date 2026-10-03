import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.integration.cost_budget import CostBudget


@pytest.fixture
def budget(tmp_path):
    return CostBudget(max_daily_budget=2.0, persist_path=tmp_path / "budget.json")


def test_initial_state(budget):
    assert budget._max_daily == 2.0
    assert budget._today_spend == 0.0
    assert not budget.is_exhausted()


def test_record_cost_accepts_within_budget(budget):
    result = budget.record_cost(0.5)
    assert result is True
    assert budget._today_spend == 0.5


def test_record_cost_rejects_exceeding_budget(budget):
    budget.record_cost(1.5)
    assert budget._today_spend == 1.5
    result = budget.record_cost(0.6)
    assert result is False
    assert budget._today_spend == 1.5


def test_record_cost_does_not_exceed_on_boundary(budget):
    budget.record_cost(2.0)
    assert budget._today_spend == 2.0
    result = budget.record_cost(0.01)
    assert result is False


def test_record_cost_zero_or_negative(budget):
    assert budget.record_cost(0.0) is True
    assert budget.record_cost(-0.5) is True
    assert budget._today_spend == 0.0


def test_budget_remaining(budget):
    assert budget.budget_remaining() == 2.0
    budget.record_cost(0.5)
    assert budget.budget_remaining() == 1.5
    budget.record_cost(1.5)
    assert budget.budget_remaining() == 0.0


def test_is_exhausted(budget):
    assert not budget.is_exhausted()
    budget.record_cost(2.0)
    assert budget.is_exhausted()


def test_reset_today(budget):
    budget.record_cost(1.0)
    budget.record_cost(1.0)
    assert budget.is_exhausted()
    budget.reset_today()
    assert not budget.is_exhausted()
    assert budget._today_spend == 0.0


def test_ensure_today_rotates_on_new_day(budget):
    budget.record_cost(1.0)
    assert budget._today_spend == 1.0
    yesterday = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400))
    budget._today_key = yesterday
    budget._ensure_today()
    assert budget._today_spend == 0.0


def test_persistence(tmp_path):
    path = tmp_path / "budget_persist.json"
    b1 = CostBudget(max_daily_budget=2.0, persist_path=path)
    b1.record_cost(0.75)
    assert b1._today_spend == 0.75

    b2 = CostBudget(max_daily_budget=2.0, persist_path=path)
    assert b2._today_spend == 0.75


def test_persistence_resets_on_new_day(tmp_path):
    path = tmp_path / "budget_old.json"
    with open(path, "w") as f:
        json.dump({"date": "2000-01-01", "spend": 1.5}, f)

    b = CostBudget(max_daily_budget=2.0, persist_path=path)
    assert b._today_spend == 0.0


def test_get_health_status(budget):
    status = budget.get_health_status()
    assert status["max_daily_budget"] == 2.0
    assert status["today_spend"] == 0.0
    assert status["budget_remaining"] == 2.0
    assert status["exhausted"] is False


def test_multiple_small_calls_within_budget(budget):
    for _ in range(100):
        result = budget.record_cost(0.01)
        assert result is True
    assert budget._today_spend == pytest.approx(1.0, rel=1e-6)


def test_large_single_call_exceeds(budget):
    result = budget.record_cost(5.0)
    assert result is False
    assert budget._today_spend == 0.0
