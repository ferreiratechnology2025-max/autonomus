from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.execution.action_executor import ActionExecutor


@pytest.fixture
def settings():
    return Settings(
        action_timeout_ms=5000,
        safe_click_margin=10,
        mouse_move_duration=0.1,
        type_interval=0.01,
        uia_click_debounce_ms=0,
        uia_enable_visual_stability_check=False,
    )


@pytest.fixture
def executor(settings):
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        mock_pg.size.return_value = (1920, 1080)
        yield ActionExecutor(settings)


@pytest.mark.asyncio
async def test_click_valid_coords(executor):
    result = await executor.click(500, 300)
    assert result is True


@pytest.mark.asyncio
async def test_click_rejects_negative_x(executor):
    result = await executor.click(-10, 300)
    assert result is False


@pytest.mark.asyncio
async def test_click_rejects_negative_y(executor):
    result = await executor.click(500, -10)
    assert result is False


@pytest.mark.asyncio
async def test_click_rejects_beyond_screen(executor):
    result = await executor.click(2000, 300)
    assert result is False


@pytest.mark.asyncio
async def test_click_rejects_beyond_screen_y(executor):
    result = await executor.click(500, 1200)
    assert result is False


@pytest.mark.asyncio
async def test_click_margin_rejects_zero_zero(executor):
    result = await executor.click(0, 0)
    assert result is False


@pytest.mark.asyncio
async def test_click_margin_rejects_near_edge(executor):
    result = await executor.click(5, 300)
    assert result is False


@pytest.mark.asyncio
async def test_double_click_valid(executor):
    result = await executor.double_click(500, 300)
    assert result is True


@pytest.mark.asyncio
async def test_right_click_valid(executor):
    result = await executor.right_click(500, 300)
    assert result is True


@pytest.mark.asyncio
async def test_move_to_valid(executor):
    result = await executor.move_to(500, 300)
    assert result is True


@pytest.mark.asyncio
async def test_move_to_rejects_invalid(executor):
    result = await executor.move_to(-1, 300)
    assert result is False


@pytest.mark.asyncio
async def test_type_text(executor):
    result = await executor.type_text("hello")
    assert result is True


@pytest.mark.asyncio
async def test_type_text_empty(executor):
    result = await executor.type_text("")
    assert result is True


@pytest.mark.asyncio
async def test_press_hotkey(executor):
    result = await executor.press_hotkey("ctrl", "c")
    assert result is True


@pytest.mark.asyncio
async def test_scroll_positive(executor):
    result = await executor.scroll(5)
    assert result is True


@pytest.mark.asyncio
async def test_scroll_negative(executor):
    result = await executor.scroll(-3)
    assert result is True


@pytest.mark.asyncio
async def test_screenshot_returns_bytes(executor):
    with patch("src.execution.action_executor.ScreenCapture") as mock_sc:
        mock_capture = AsyncMock()
        mock_capture.capture.return_value = b"fake_png_bytes"
        mock_sc.return_value = mock_capture
        result = await executor.screenshot()
    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_timeout_triggers_on_slow_action(executor):
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        import time as mock_time

        original_time = __import__("time")

        def slow_click(*args, **kwargs):
            original_time.sleep(0.5)
            return None

        mock_pg.click.side_effect = slow_click
        mock_pg.size.return_value = (1920, 1080)
        executor._timeout_ms = 100
        result = await executor.click(500, 300)
    assert result is False


@pytest.mark.asyncio
async def test_execute_with_timeout_success(executor):
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        mock_pg.size.return_value = (1920, 1080)

        def fast_action():
            return True

        result = await executor._execute_with_timeout("test", fast_action)
        assert result is True


@pytest.mark.asyncio
async def test_click_element_returns_false_without_uia(executor):
    result = await executor.click_element("name", "OK Button")
    assert result is False


@pytest.mark.asyncio
async def test_click_element_honors_debounce():
    settings = Settings(
        action_timeout_ms=5000,
        safe_click_margin=10,
        mouse_move_duration=0.1,
        type_interval=0.01,
        uia_click_debounce_ms=100,
        uia_enable_visual_stability_check=False,
    )
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        mock_pg.size.return_value = (1920, 1080)
        uia_mock = MagicMock()
        element_mock = MagicMock()
        element_mock.center = (500, 300)
        uia_mock.find_element_async = AsyncMock(return_value=element_mock)
        uia_mock.get_clickable_coordinates_async = AsyncMock(return_value=(500, 300))
        uia_mock.get_active_window_hwnd_async = AsyncMock(return_value=None)

        executor = ActionExecutor(settings, uia=uia_mock)
        result = await executor.click_element("name", "test")
        assert result is True
        uia_mock.find_element_async.assert_called_once()


@pytest.mark.asyncio
async def test_click_element_waits_for_stability():
    settings = Settings(
        action_timeout_ms=5000,
        safe_click_margin=10,
        mouse_move_duration=0.1,
        type_interval=0.01,
        uia_click_debounce_ms=0,
        uia_enable_visual_stability_check=True,
    )
    with (
        patch("src.execution.action_executor.pyautogui") as mock_pg,
    ):
        mock_pg.size.return_value = (1920, 1080)

        uia_mock = MagicMock()
        element_mock = MagicMock()
        element_mock.center = (500, 300)
        uia_mock.find_element_async = AsyncMock(return_value=element_mock)
        uia_mock.get_clickable_coordinates_async = AsyncMock(return_value=(500, 300))
        uia_mock.get_active_window_hwnd_async = AsyncMock(return_value=None)

        executor = ActionExecutor(settings, uia=uia_mock)
        executor._wait_for_stable_screen = AsyncMock(return_value=True)
        result = await executor.click_element("name", "test")
        assert result is True


@pytest.mark.asyncio
async def test_wait_for_stable_screen_returns_true():
    import io
    import numpy as np
    from PIL import Image

    arr = np.full((50, 50, 3), 128, dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    frame = buf.getvalue()

    with patch("src.execution.action_executor.ScreenCapture") as mock_sc:
        capture_instance = AsyncMock()
        capture_instance.capture.return_value = frame
        mock_sc.return_value = capture_instance

        settings = Settings(action_timeout_ms=5000, safe_click_margin=10)
        executor = ActionExecutor(settings)
        result = await executor._wait_for_stable_screen(timeout_ms=300)
        assert result is True


@pytest.mark.asyncio
async def test_lightweight_similarity_identical():
    settings = Settings(action_timeout_ms=5000, safe_click_margin=10)
    executor = ActionExecutor.__new__(ActionExecutor)
    executor._config = settings

    from PIL import Image
    import io
    import numpy as np
    arr = np.full((50, 50, 3), 128, dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    sim = executor._lightweight_similarity(data, data)
    assert sim > 0.99


@pytest.mark.asyncio
async def test_lightweight_similarity_different():
    settings = Settings(action_timeout_ms=5000, safe_click_margin=10)
    executor = ActionExecutor.__new__(ActionExecutor)
    executor._config = settings

    from PIL import Image
    import io
    import numpy as np
    white = np.full((50, 50, 3), 255, dtype=np.uint8)
    black = np.full((50, 50, 3), 0, dtype=np.uint8)
    buf1 = io.BytesIO()
    buf2 = io.BytesIO()
    Image.fromarray(white).save(buf1, format="PNG")
    Image.fromarray(black).save(buf2, format="PNG")

    sim = executor._lightweight_similarity(buf1.getvalue(), buf2.getvalue())
    assert sim < 1.0


@pytest.mark.asyncio
async def test_is_hwnd_related_negative():
    assert ActionExecutor._is_hwnd_related(-1, -2) is False


@pytest.mark.asyncio
async def test_is_hwnd_related_different():
    assert ActionExecutor._is_hwnd_related(1, 999999) is False


@pytest.mark.asyncio
async def test_get_pid_invalid():
    assert ActionExecutor._get_pid(-1) is None


@pytest.mark.asyncio
async def test_get_pid_zero():
    assert ActionExecutor._get_pid(0) is None


@pytest.mark.asyncio
async def test_lightweight_similarity_empty():
    settings = Settings(action_timeout_ms=5000, safe_click_margin=10)
    executor = ActionExecutor.__new__(ActionExecutor)
    executor._config = settings

    sim = executor._lightweight_similarity(b"", b"")
    assert sim == 0.0


@pytest.mark.asyncio
async def test_context_lock_acquires_and_releases():
    settings = Settings(
        action_timeout_ms=5000,
        safe_click_margin=10,
        mouse_move_duration=0.1,
        type_interval=0.01,
        uia_click_debounce_ms=0,
        uia_enable_visual_stability_check=False,
        context_lock_timeout_ms=5000,
    )
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        mock_pg.size.return_value = (1920, 1080)
        uia_mock = MagicMock()
        element_mock = MagicMock()
        element_mock.center = (500, 300)
        uia_mock.find_element_async = AsyncMock(return_value=element_mock)
        uia_mock.get_clickable_coordinates_async = AsyncMock(return_value=(500, 300))
        uia_mock.get_active_window_hwnd_async = AsyncMock(return_value=None)

        executor = ActionExecutor(settings, uia=uia_mock)

        # Lock should be free initially — first call acquires and releases
        result = await executor.click_element("name", "first")
        assert result is True

        # Second call should also succeed (lock was released)
        result = await executor.click_element("name", "second")
        assert result is True


@pytest.mark.asyncio
async def test_context_lock_timeout_when_held():
    settings = Settings(
        action_timeout_ms=5000,
        safe_click_margin=10,
        mouse_move_duration=0.1,
        type_interval=0.01,
        uia_click_debounce_ms=500,
        uia_enable_visual_stability_check=False,
        context_lock_timeout_ms=100,
    )
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        mock_pg.size.return_value = (1920, 1080)
        uia_mock = MagicMock()
        element_mock = MagicMock()
        element_mock.center = (500, 300)
        uia_mock.find_element_async = AsyncMock(return_value=element_mock)
        uia_mock.get_clickable_coordinates_async = AsyncMock(return_value=(500, 300))
        uia_mock.get_active_window_hwnd_async = AsyncMock(return_value=None)

        executor = ActionExecutor(settings, uia=uia_mock)

        # Acquire the lock manually to simulate a stuck operation
        await executor._context_lock.acquire()

        # Second call should time out
        result = await executor.click_element("name", "button")
        assert result is False

        # Release so test cleanup doesn't hang
        executor._context_lock.release()
