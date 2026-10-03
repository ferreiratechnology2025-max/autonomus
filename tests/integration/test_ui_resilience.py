import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from src.core.config import Settings
from src.execution.action_executor import ActionExecutor
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.perception.ocr import OCRProcessor
from src.perception.ui_detector import UIDetector
from src.planning.models import RepairStrategy, Task, TaskStatus
from src.planning.repair_engine import RepairEngine
from src.planning.validator import Validator


def _make_image_bytes(color: int = 255, size: tuple = (100, 100)) -> bytes:
    arr = np.full((*size, 3), color, dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def settings():
    return Settings(
        action_timeout_ms=500,
        safe_click_margin=10,
        mouse_move_duration=0.1,
        type_interval=0.01,
        enable_ocr_fallback=True,
        calibration_deterministic=True,
    )


@pytest.fixture
def executor(settings):
    with patch("src.execution.action_executor.pyautogui") as mock_pg:
        mock_pg.size.return_value = (1920, 1080)
        yield ActionExecutor(settings)


class TestResolutionChange:
    @pytest.mark.asyncio
    async def test_detector_fallback_on_resolution_mismatch(self):
        detector = UIDetector()
        large_img = _make_image_bytes(128, size=(200, 150))
        results = await detector.find_buttons_by_color(large_img)
        assert isinstance(results, list)


class TestOCRFailure:
    @pytest.mark.asyncio
    async def test_validator_returns_false_when_ocr_fails_and_no_uia(self):
        ocr = MagicMock(spec=OCRProcessor)
        ocr.extract_text = AsyncMock(return_value="")

        task = MagicMock()
        task.postcondition = "text_appeared"
        task.element_name = None
        task.expected_text = None

        validator = Validator(ocr=ocr)
        pre = _make_image_bytes(255)
        post = _make_image_bytes(255)
        result = await validator.validate(task, pre, post)
        assert result is False

    @pytest.mark.asyncio
    async def test_validator_uses_ocr_fallback_text_appears(self):
        ocr = MagicMock(spec=OCRProcessor)
        ocr.extract_text = AsyncMock(return_value="hello world")

        task = MagicMock()
        task.postcondition = "text_appeared"
        task.element_name = None
        task.expected_text = None

        validator = Validator(ocr=ocr)
        pre = _make_image_bytes(255)
        post = _make_image_bytes(255)
        result = await validator.validate(task, pre, post)
        assert result is True


class TestInvalidCoordinates:
    @pytest.mark.asyncio
    async def test_executor_rejects_out_of_bounds(self, executor):
        with patch("src.execution.action_executor.pyautogui") as mock_pg:
            mock_pg.size.return_value = (1920, 1080)
            result = await executor.click(9999, 9999)
            assert result is False

    @pytest.mark.asyncio
    async def test_executor_rejects_negative_coords(self, executor):
        result = await executor.click(-1, -1)
        assert result is False

    @pytest.mark.asyncio
    async def test_executor_rejects_zero_zero_within_margin(self, executor):
        result = await executor.click(0, 0)
        assert result is False

    @pytest.mark.asyncio
    async def test_move_to_rejects_invalid(self, executor):
        result = await executor.move_to(-100, 300)
        assert result is False


class TestActionTimeout:
    @pytest.mark.asyncio
    async def test_timeout_on_slow_action(self, executor):
        with patch("src.execution.action_executor.pyautogui") as mock_pg:
            import time

            def slow_click(*args, **kwargs):
                time.sleep(1.0)
                return None

            mock_pg.click.side_effect = slow_click
            mock_pg.size.return_value = (1920, 1080)
            executor._timeout_ms = 50
            result = await executor.click(500, 300)
            assert result is False


@pytest.fixture
def mock_router():
    router = MagicMock(spec=ModelRouter)
    router.generate = AsyncMock(
        return_value=MagicMock(text="retry with offset", model_used="ollama/test", cost=0, metadata={}, success=True)
    )
    return router


@pytest.fixture
def mock_detector():
    detector = MagicMock(spec=SensitiveDataDetector)
    detector.has_sensitive_data = MagicMock(return_value=False)
    return detector


class TestRepairEngineFallback:
    @pytest.mark.asyncio
    async def test_repair_engine_retry_on_failure(self, mock_router, mock_detector):
        engine = RepairEngine(mock_router, mock_detector)
        task = Task(name="click_button", action_type="click", parameters={"x": 500, "y": 300})
        engine._execute_action_simple = AsyncMock(return_value=True)
        success, strategy = await engine.repair(task, Exception("button_not_found"), {})
        assert success is True
        assert strategy == RepairStrategy.RETRY

    @pytest.mark.asyncio
    async def test_repair_engine_escalates_after_all_strategies_fail(self, mock_router, mock_detector):
        mock_router.generate = AsyncMock(
            return_value=MagicMock(text="", model_used="degraded", cost=0, metadata={}, success=False)
        )
        engine = RepairEngine(mock_router, mock_detector)
        task = Task(name="click_button", action_type="click", parameters={"x": 500, "y": 300})
        engine._execute_action_simple = AsyncMock(return_value=False)
        success, strategy = await engine.repair(task, Exception("button_not_found"), {})
        assert success is False
        assert strategy == RepairStrategy.ABORT
        assert task.status == TaskStatus.FAILED


class TestUIAResilience:
    @pytest.mark.asyncio
    async def test_uia_wrapper_missing_package_fallback(self):
        with patch("src.perception.uia_wrapper._UIA_AVAILABLE", False):
            from src.perception.uia_wrapper import UIAWrapper

            wrapper = UIAWrapper()
            with pytest.raises(RuntimeError, match="uiautomation package is not installed"):
                wrapper.find_element("name", "test")

    @pytest.mark.asyncio
    async def test_click_element_returns_false_without_uia(self, executor):
        result = await executor.click_element("name", "OK Button")
        assert result is False

    @pytest.mark.asyncio
    async def test_validator_fallback_when_uia_unavailable(self):
        task = MagicMock()
        task.postcondition = "text_appeared"
        task.element_name = "Welcome"

        validator = Validator()
        pre = _make_image_bytes(255)
        post = _make_image_bytes(255)
        result = await validator.validate(task, pre, post)
        assert result is True
