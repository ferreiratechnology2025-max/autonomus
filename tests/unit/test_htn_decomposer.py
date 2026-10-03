from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.planning.htn_decomposer import HTNDecomposer


@pytest.fixture
def mock_router():
    router = MagicMock(spec=ModelRouter)
    router.generate = AsyncMock(
        return_value=MagicMock(
            text='[{"action_type": "click", "parameters": {"x": 100, "y": 200}}]',
            model_used="ollama/test",
            cost=0.0,
            metadata={},
            success=True,
        )
    )
    return router


@pytest.fixture
def mock_detector():
    detector = MagicMock(spec=SensitiveDataDetector)
    detector.has_sensitive_data = MagicMock(return_value=False)
    return detector


@pytest.mark.asyncio
async def test_decompose_open_app(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    task = await decomposer.decompose("open_app", {"app_name": "notepad"})
    assert task.name == "open_app"
    assert len(task.subtasks) == 3
    assert task.subtasks[0].action_type == "press_hotkey"


@pytest.mark.asyncio
async def test_decompose_login(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    task = await decomposer.decompose("login", {"username": "admin", "password": "secret"})
    assert task.name == "login"
    assert len(task.subtasks) == 3
    assert task.subtasks[0].action_type == "type_text"


@pytest.mark.asyncio
async def test_decompose_search(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    task = await decomposer.decompose("search", {"query": "jarvis"})
    assert task.name == "search"
    assert len(task.subtasks) == 3
    assert task.subtasks[2].action_type == "press_hotkey"


@pytest.mark.asyncio
async def test_decompose_fill_form(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    task = await decomposer.decompose("fill_form", {"fields": [{"value": "john"}, {"value": "doe"}]})
    assert task.name == "fill_form"
    assert len(task.subtasks) == 4


@pytest.mark.asyncio
async def test_decompose_fallback(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    task = await decomposer.decompose("unknown goal no match")
    assert task.name == "unknown goal no match"
    assert len(task.subtasks) == 1
    assert task.subtasks[0].action_type == "click"


@pytest.mark.asyncio
async def test_decompose_with_llm(mock_router, mock_detector):
    mock_detector.has_sensitive_data = MagicMock(return_value=False)
    decomposer = HTNDecomposer(mock_router, mock_detector)
    task = await decomposer.decompose("custom goal")
    assert len(task.subtasks) == 1
    assert task.subtasks[0].action_type == "click"


def test_goal_similar(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    assert decomposer._goal_similar("open notepad", "open notepad and type") is True
    assert decomposer._goal_similar("open notepad", "delete all files") is False


def test_goal_similar_empty(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    assert decomposer._goal_similar("", "something") is False


@pytest.mark.asyncio
async def test_reuse_pattern(mock_router, mock_detector):
    decomposer = HTNDecomposer(mock_router, mock_detector)
    episode = {"goal": "past goal", "actions": {"action_type": "click"}}
    task = await decomposer._reuse_pattern("new goal", episode)
    assert task.name == "new goal"
