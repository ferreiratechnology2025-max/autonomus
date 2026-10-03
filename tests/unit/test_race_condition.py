import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.execution.action_executor import ActionExecutor, RaceConditionError


@pytest.fixture
def executor():
    config = MagicMock()
    config.action_timeout_ms = 5000
    config.safe_click_margin = 10
    config.mouse_move_duration = 0.1
    config.type_interval = 0.05
    config.context_lock_timeout_ms = 5000
    config.uia_click_debounce_ms = 0
    config.uia_enable_visual_stability_check = False
    return ActionExecutor(config)


@pytest.mark.asyncio
async def test_race_condition_detected_on_hwnd_change(executor):
    with patch.object(executor, '_get_foreground_hwnd') as mock_hwnd:
        mock_hwnd.side_effect = [12345, 67890]
        with patch.object(executor, '_is_child_window') as mock_child:
            mock_child.return_value = False
            with patch.object(executor, '_execute_with_timeout', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = True
                with pytest.raises(RaceConditionError):
                    await executor.click(100, 200)


@pytest.mark.asyncio
async def test_child_window_is_allowed(executor):
    with patch.object(executor, '_get_foreground_hwnd') as mock_hwnd:
        mock_hwnd.side_effect = [100, 200]
        with patch.object(executor, '_is_child_window') as mock_child:
            mock_child.return_value = True
            with patch.object(executor, '_execute_with_timeout', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = True
                result = await executor.click(100, 200)
                assert result is True


@pytest.mark.asyncio
async def test_same_hwnd_no_race_condition(executor):
    with patch.object(executor, '_get_foreground_hwnd') as mock_hwnd:
        mock_hwnd.side_effect = [12345, 12345]
        with patch.object(executor, '_execute_with_timeout', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True
            result = await executor.click(100, 200)
            assert result is True


@pytest.mark.asyncio
async def test_race_condition_error_message(executor):
    with patch.object(executor, '_get_foreground_hwnd') as mock_hwnd:
        mock_hwnd.side_effect = [1000, 2000]
        with patch.object(executor, '_is_child_window') as mock_child:
            mock_child.return_value = False
            with patch.object(executor, '_execute_with_timeout', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = True
                with pytest.raises(RaceConditionError) as exc_info:
                    await executor.click(100, 200)
                assert "HWND mudou" in str(exc_info.value)
                assert "1000" in str(exc_info.value)
                assert "2000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_is_child_window_positive():
    executor = ActionExecutor(MagicMock())
    with patch("src.execution.action_executor._user32.GetParent") as mock_parent:
        mock_parent.side_effect = [200, 100, 0]
        assert executor._is_child_window(100, 300) is True


@pytest.mark.asyncio
async def test_is_child_window_negative():
    executor = ActionExecutor(MagicMock())
    with patch("src.execution.action_executor._user32.GetParent") as mock_parent:
        mock_parent.side_effect = [999, 888, 0]
        assert executor._is_child_window(100, 300) is False


def test_race_condition_error_is_exception():
    assert issubclass(RaceConditionError, Exception)
    err = RaceConditionError("test error")
    assert str(err) == "test error"
