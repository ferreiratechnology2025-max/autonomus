from pathlib import Path

import pytest
import pytest_asyncio

from src.memory.db_manager import DatabaseManager
from src.memory.memory import MemorySystem
from src.memory.models import StateDiff


@pytest_asyncio.fixture
async def memory(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.db")
    await mgr.initialize()
    mem = MemorySystem(mgr)
    yield mem
    await mgr.close()


@pytest.mark.asyncio
async def test_start_episode(memory):
    ep_id = await memory.start_episode(goal="click save button", model_used="gpt4")
    assert ep_id is not None
    assert memory.current_episode_id == ep_id
    assert memory.action_counter == 0


@pytest.mark.asyncio
async def test_end_episode(memory):
    await memory.start_episode("test")
    await memory.end_episode(outcome="success", duration_ms=500)
    assert memory.current_episode_id is None


@pytest.mark.asyncio
async def test_full_episode_lifecycle(memory):
    ep_id = await memory.start_episode("fill form")

    act1 = await memory.record_action("click", {"x": 100, "y": 200}, "success", 50)
    act2 = await memory.record_action("type", {"text": "hello"}, "success", 100, error_msg=None)
    act3 = await memory.record_action("click", {"x": 300, "y": 400}, "failed", 200, error_msg="timeout")

    await memory.end_episode("failed", 350)

    assert act1 is not None
    assert act2 is not None
    assert act3 is not None


@pytest.mark.asyncio
async def test_record_diff(memory):
    await memory.start_episode("test")
    act_id = await memory.record_action("click", {"x": 10, "y": 20}, "success", 30)

    diff = StateDiff(
        diff_id="diff1",
        action_id=act_id,
        pre_screenshot_hash="hash_pre",
        post_screenshot_hash="hash_post",
        visual_divergence=0.1,
    )
    await memory.record_diff(act_id, diff)


@pytest.mark.asyncio
async def test_get_recent_successes_empty(memory):
    results = await memory.get_recent_successes(limit=10)
    assert results == []


@pytest.mark.asyncio
async def test_get_recent_successes_with_data(memory):
    await memory.start_episode("test")
    await memory.record_action("click", {"x": 100}, "success", 30)
    await memory.record_action("type", {"text": "hi"}, "failed", 50)
    await memory.end_episode("failed", 100)

    await memory.start_episode("test2")
    await memory.record_action("click", {"x": 200}, "success", 40)
    await memory.end_episode("success", 200)

    successes = await memory.get_recent_successes(limit=10)
    assert len(successes) == 2


@pytest.mark.asyncio
async def test_get_recent_successes_filtered(memory):
    await memory.start_episode("test")
    await memory.record_action("click", {"x": 100}, "success", 30)
    await memory.record_action("type", {"text": "hi"}, "success", 50)
    await memory.end_episode("success", 100)

    successes = await memory.get_recent_successes(limit=10, action_type="click")
    assert len(successes) == 1


@pytest.mark.asyncio
async def test_get_failure_patterns(memory):
    await memory.start_episode("test")
    await memory.record_action("click", {"x": 100}, "failed", 30, error_msg="timeout")
    await memory.record_action("click", {"x": 200}, "failed", 30, error_msg="timeout")
    await memory.record_action("type", {"text": "hi"}, "failed", 50, error_msg="element not found")
    await memory.end_episode("failed", 200)

    patterns = await memory.get_failure_patterns(limit=50)
    assert len(patterns) >= 1
