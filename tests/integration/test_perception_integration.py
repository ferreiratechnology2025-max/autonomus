import io

import numpy as np
import pytest
from PIL import Image

from src.core.config import Settings
from src.perception.ocr import OCRProcessor
from src.perception.screen_capture import ScreenCapture
from src.perception.ui_detector import UIDetector


@pytest.mark.slow
def test_screen_capture_actual_screen():
    capture = ScreenCapture(monitor=1)
    size = capture.get_screen_size()
    assert size[0] > 0
    assert size[1] > 0


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ocr_with_real_image():
    img = Image.fromarray(np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    settings = Settings(tesseract_path="tesseract")
    ocr = OCRProcessor(settings)
    text = await ocr.extract_text(image_bytes)
    assert isinstance(text, str)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ui_detector_with_real_image():
    img = Image.fromarray(np.ones((200, 300, 3), dtype=np.uint8) * 255)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    detector = UIDetector()
    buttons = await detector.find_buttons_by_color(image_bytes)
    assert isinstance(buttons, list)
