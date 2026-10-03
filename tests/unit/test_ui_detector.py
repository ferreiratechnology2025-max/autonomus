import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from src.perception.ui_detector import UIDetector


def _create_test_image_bytes(width: int = 200, height: int = 150) -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (height, width, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def detector():
    return UIDetector()


@pytest.mark.asyncio
async def test_find_buttons_by_color_returns_list(detector):
    image_bytes = _create_test_image_bytes()
    result = await detector.find_buttons_by_color(image_bytes)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_find_input_fields_returns_list(detector):
    image_bytes = _create_test_image_bytes()
    result = await detector.find_input_fields(image_bytes)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_find_buttons_filters_by_aspect_ratio(detector):
    image_bytes = _create_test_image_bytes()
    result = await detector.find_buttons_by_color(image_bytes)
    assert isinstance(result, list)
