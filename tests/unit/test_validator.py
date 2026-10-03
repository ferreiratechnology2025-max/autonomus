import io
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from PIL import Image

from src.planning.models import Task
from src.planning.validator import Validator


def _make_image_bytes(color: int = 255, size: tuple = (100, 100)) -> bytes:
    arr = np.full((*size, 3), color, dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_validate_default_returns_true():
    validator = Validator()
    task = Task(name="test", action_type="click")
    result = await validator.validate(task, b"", b"")
    assert result is True


@pytest.mark.asyncio
async def test_validate_text_appeared():
    ocr = MagicMock()
    ocr.extract_text = AsyncMock(return_value="hello world")
    validator = Validator(ocr=ocr)
    task = Task(name="test", postcondition="text_appeared")
    result = await validator.validate(task, b"pre", b"post")
    assert result is True


@pytest.mark.asyncio
async def test_validate_text_not_appeared():
    ocr = MagicMock()
    ocr.extract_text = AsyncMock(return_value="")
    validator = Validator(ocr=ocr)
    task = Task(name="test", postcondition="text_appeared")
    result = await validator.validate(task, b"pre", b"post")
    assert result is False


@pytest.mark.asyncio
async def test_validate_window_changed():
    validator = Validator()
    task = Task(name="test", postcondition="window_changed")
    white = _make_image_bytes(255)
    black = _make_image_bytes(0)
    result = await validator.validate(task, white, black)
    assert result is True


@pytest.mark.asyncio
async def test_validate_window_same():
    validator = Validator()
    task = Task(name="test", postcondition="window_changed")
    white = _make_image_bytes(255)
    result = await validator.validate(task, white, white)
    assert result is False


def test_calculate_similarity_identical():
    validator = Validator()
    img = _make_image_bytes(128)
    sim = validator._calculate_similarity(img, img)
    assert sim > 0.99


def test_calculate_similarity_different():
    validator = Validator()
    white = _make_image_bytes(255)
    black = _make_image_bytes(0)
    sim = validator._calculate_similarity(white, black)
    assert sim < 0.5


@pytest.mark.asyncio
async def test_validate_text_appeared_with_uia():
    ocr = MagicMock()
    ocr.extract_text = AsyncMock(return_value="hello world")
    uia = MagicMock()
    uia.get_active_window_class_async = AsyncMock(return_value="Notepad")
    uia.find_element_async = AsyncMock(return_value=MagicMock())

    validator = Validator(ocr=ocr, uia=uia)
    task = MagicMock()
    task.postcondition = "text_appeared"
    task.element_name = "Welcome"
    task.expected_text = None
    result = await validator.validate(task, b"pre", b"post")
    assert result is True
    uia.find_element_async.assert_called_once()


@pytest.mark.asyncio
async def test_validate_web_app_uses_hybrid():
    ocr = MagicMock()
    ocr.extract_text = AsyncMock(return_value="hello")
    uia = MagicMock()
    uia.get_active_window_class_async = AsyncMock(return_value="Chrome_WidgetWin_1")
    uia.find_element_async = AsyncMock(return_value=None)

    validator = Validator(ocr=ocr, uia=uia)
    task = MagicMock()
    task.postcondition = "text_appeared"
    task.element_name = "Button"
    task.expected_text = None
    result = await validator.validate(task, b"pre", b"post")
    assert result is True
    uia.find_element_async.assert_called_once()
    ocr.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_validate_no_ocr_no_uia():
    validator = Validator()
    task = Task(name="test", postcondition="text_appeared")
    result = await validator.validate(task, b"pre", b"post")
    assert result is True


@pytest.mark.asyncio
async def test_get_window_strategy():
    uia = MagicMock()
    uia.get_active_window_class_async = AsyncMock(return_value="Notepad")

    validator = Validator(uia=uia)
    strategy = await validator._get_window_strategy()
    assert strategy == "UIA_PRIMARY"
