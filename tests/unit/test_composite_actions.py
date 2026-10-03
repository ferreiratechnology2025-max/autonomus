from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.execution.composite_actions import CompositeActions


@pytest.fixture
def mock_executor():
    m = MagicMock()
    m.press_hotkey = AsyncMock(return_value=True)
    m.type_text = AsyncMock(return_value=True)
    return m


@pytest.fixture
def comp(mock_executor):
    return CompositeActions(mock_executor)


@pytest.mark.asyncio
async def test_select_all_and_copy(comp, mock_executor):
    result = await comp.select_all_and_copy()
    assert result is True
    assert mock_executor.press_hotkey.await_count == 2
    mock_executor.press_hotkey.assert_any_call("ctrl", "a")
    mock_executor.press_hotkey.assert_any_call("ctrl", "c")


@pytest.mark.asyncio
async def test_paste(comp, mock_executor):
    result = await comp.paste()
    assert result is True
    mock_executor.press_hotkey.assert_awaited_once_with("ctrl", "v")


@pytest.mark.asyncio
async def test_press_enter(comp, mock_executor):
    result = await comp.press_enter()
    assert result is True
    mock_executor.press_hotkey.assert_awaited_once_with("enter")


@pytest.mark.asyncio
async def test_press_tab_once(comp, mock_executor):
    result = await comp.press_tab(times=1)
    assert result is True
    mock_executor.press_hotkey.assert_awaited_once_with("tab")


@pytest.mark.asyncio
async def test_press_tab_multiple(comp, mock_executor):
    result = await comp.press_tab(times=3)
    assert result is True
    assert mock_executor.press_hotkey.await_count == 3


@pytest.mark.asyncio
async def test_press_escape(comp, mock_executor):
    result = await comp.press_escape()
    assert result is True
    mock_executor.press_hotkey.assert_awaited_once_with("esc")
