import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.core.main_loop import JarvisMainLoop


@pytest.fixture
def settings():
    return Settings(
        health_check_interval_seconds=9999,
        metrics_flush_interval_seconds=9999,
        task_queue_max_size=10,
    )


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock()
    orch.initialize = AsyncMock()
    orch.execute_goal = AsyncMock(return_value={"success": True, "plan_id": "test"})
    return orch


@pytest.mark.asyncio
async def test_submit_and_process_task(settings, mock_orchestrator):
    loop = JarvisMainLoop(mock_orchestrator, settings)
    loop.running = True

    loop.submit_task("test goal", {"key": "value"})
    task = await asyncio.wait_for(loop.task_queue.get(), timeout=1.0)
    assert task["goal"] == "test goal"
    assert task["context"]["key"] == "value"


@pytest.mark.asyncio
async def test_process_task_calls_orchestrator(settings, mock_orchestrator):
    loop = JarvisMainLoop(mock_orchestrator, settings)

    with patch.object(loop, "_process_task_loop") as mock_process:
        mock_process.return_value = None
        loop.submit_task("goal")
        loop.running = False

        item = await asyncio.wait_for(loop.task_queue.get(), timeout=1.0)
        assert item["goal"] == "goal"


@pytest.mark.asyncio
async def test_stop_sets_running_false(settings, mock_orchestrator):
    loop = JarvisMainLoop(mock_orchestrator, settings)
    loop.running = True
    await loop.stop()
    assert loop.running is False


def test_submit_task_no_context(settings, mock_orchestrator):
    loop = JarvisMainLoop(mock_orchestrator, settings)
    loop.submit_task("simple goal")
    assert loop.task_queue.qsize() == 1


@pytest.mark.asyncio
async def test_queue_max_size(settings, mock_orchestrator):
    loop = JarvisMainLoop(mock_orchestrator, settings)
    for i in range(settings.task_queue_max_size):
        loop.submit_task(f"goal_{i}")
    assert loop.task_queue.qsize() == settings.task_queue_max_size
