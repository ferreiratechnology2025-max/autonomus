import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from src.core.config import Settings
from src.perception.ocr import OCRProcessor


def _create_test_image_bytes(width: int = 50, height: int = 20) -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (height, width, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def ocr():
    with (
        patch("src.perception.ocr.pytesseract.get_tesseract_version") as mock_ver,
        patch("src.perception.ocr.pytesseract.image_to_string") as mock_str,
        patch("src.perception.ocr.pytesseract.image_to_data") as mock_data,
    ):
        mock_ver.return_value = "5.3.0"
        mock_str.return_value = ""
        mock_data.return_value = {
            "text": [""],
            "left": [0],
            "top": [0],
            "width": [0],
            "height": [0],
            "conf": [0],
        }
        settings = Settings(tesseract_path="tesseract", enable_ocr_fallback=True)
        yield OCRProcessor(settings)


@pytest.mark.asyncio
async def test_extract_text_returns_string(ocr):
    with patch("src.perception.ocr.pytesseract.image_to_string") as mock_str:
        mock_str.return_value = "Hello World"
        image_bytes = _create_test_image_bytes()
        result = await ocr.extract_text(image_bytes)
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_extract_text_with_boxes_returns_list(ocr):
    mock_data = {
        "text": ["Hello", "World"],
        "left": [10, 50],
        "top": [20, 60],
        "width": [30, 40],
        "height": [15, 20],
        "conf": [95, 90],
    }

    with patch("src.perception.ocr.pytesseract.image_to_data") as mock_d:
        mock_d.return_value = mock_data
        image_bytes = _create_test_image_bytes()
        result = await ocr.extract_text_with_boxes(image_bytes)

    assert isinstance(result, list)
    assert len(result) >= 1
    assert "text" in result[0]
    assert "bbox" in result[0]


@pytest.mark.asyncio
async def test_find_text_found(ocr):
    with patch.object(ocr, "extract_text_with_boxes") as mock_extract:
        mock_extract.return_value = [
            {"text": "Click Here", "bbox": [10, 20, 100, 40], "confidence": 0.95},
        ]
        result = await ocr.find_text(b"", "Click Here")

    assert result is not None
    assert result["text"] == "Click Here"


@pytest.mark.asyncio
async def test_find_text_not_found(ocr):
    with patch.object(ocr, "extract_text_with_boxes") as mock_extract:
        mock_extract.return_value = [
            {"text": "Other", "bbox": [10, 20, 100, 40], "confidence": 0.95},
        ]
        result = await ocr.find_text(b"", "Missing")

    assert result is None


@pytest.mark.asyncio
async def test_graceful_fallback_when_tesseract_missing():
    with patch("src.perception.ocr.pytesseract.get_tesseract_version") as mock_ver:
        mock_ver.side_effect = Exception("Tesseract not found")
        settings = Settings(tesseract_path="/nonexistent/tesseract")
        ocr = OCRProcessor(settings)
        result = await ocr.extract_text(b"")
    assert result == ""


@pytest.mark.asyncio
async def test_find_text_case_insensitive(ocr):
    with patch.object(ocr, "extract_text_with_boxes") as mock_extract:
        mock_extract.return_value = [
            {"text": "click here", "bbox": [10, 20, 100, 40], "confidence": 0.95},
        ]
        result = await ocr.find_text(b"", "Click Here")
    assert result is not None
    assert result["text"] == "click here"
