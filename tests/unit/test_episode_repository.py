import json
from pathlib import Path

import pytest
import pytest_asyncio

from src.memory.db_manager import DatabaseManager
from src.memory.episode_repository import EpisodeRepository
from src.memory.models import ActionRecord, Episode, StateDiff


@pytest_asyncio.fixture
async def db(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.db")
    await mgr.initialize()
    yield mgr
    await mgr.close()


@pytest_asyncio.fixture
async def repo(db):
    return EpisodeRepository(db)


@pytest.mark.asyncio
async def test_create_episode(repo):
    ep = Episode(episode_id="ep1", timestamp=1000.0, goal="test goal", outcome="success", duration_ms=500)
    ep_id = await repo.create(ep)
    assert ep_id == "ep1"


@pytest.mark.asyncio
async def test_get_episode(repo):
    ep = Episode(episode_id="ep2", timestamp=2000.0, goal="find button", outcome="failed", duration_ms=300)
    await repo.create(ep)
    result = await repo.get("ep2")
    assert result is not None
    assert result.episode_id == "ep2"
    assert result.goal == "find button"
    assert result.outcome == "failed"


@pytest.mark.asyncio
async def test_get_nonexistent_episode(repo):
    result = await repo.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_recent_empty(repo):
    results = await repo.list_recent(limit=10)
    assert results == []


@pytest.mark.asyncio
async def test_list_recent_with_data(repo):
    await repo.create(Episode(episode_id="a", timestamp=100.0, goal="g1", outcome="success", duration_ms=100))
    await repo.create(Episode(episode_id="b", timestamp=200.0, goal="g2", outcome="failed", duration_ms=200))
    results = await repo.list_recent(limit=10)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_list_recent_filter_by_outcome(repo):
    await repo.create(Episode(episode_id="a", timestamp=100.0, goal="g1", outcome="success", duration_ms=100))
    await repo.create(Episode(episode_id="b", timestamp=200.0, goal="g2", outcome="failed", duration_ms=200))
    results = await repo.list_recent(limit=10, outcome="success")
    assert len(results) == 1
    assert results[0].episode_id == "a"


@pytest.mark.asyncio
async def test_update_outcome(repo):
    await repo.create(Episode(episode_id="ep1", timestamp=100.0, goal="test", outcome="running", duration_ms=0))
    await repo.update_outcome("ep1", "success", 1500)
    result = await repo.get("ep1")
    assert result is not None
    assert result.outcome == "success"
    assert result.duration_ms == 1500


@pytest.mark.asyncio
async def test_add_action(repo):
    await repo.create(Episode(episode_id="ep1", timestamp=100.0, goal="test", outcome="running", duration_ms=0))
    action = ActionRecord(
        action_id="act1",
        episode_id="ep1",
        sequence=1,
        action_type="click",
        parameters={"x": 100, "y": 200},
        outcome="success",
        execution_time_ms=50,
    )
    await repo.add_action(action)


@pytest.mark.asyncio
async def test_add_action_and_diff(repo):
    await repo.create(Episode(episode_id="ep1", timestamp=100.0, goal="test", outcome="running", duration_ms=0))
    action = ActionRecord(
        action_id="act1",
        episode_id="ep1",
        sequence=1,
        action_type="click",
        parameters={"x": 100},
        outcome="success",
        execution_time_ms=50,
    )
    await repo.add_action(action)

    diff = StateDiff(
        diff_id="diff1",
        action_id="act1",
        pre_screenshot_hash="abc",
        post_screenshot_hash="def",
        visual_divergence=0.05,
        text_added="Submit",
        text_removed=None,
        window_changed=False,
    )
    await repo.add_diff(diff)
