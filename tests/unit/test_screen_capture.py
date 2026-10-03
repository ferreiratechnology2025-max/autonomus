from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.perception.screen_capture import ScreenCapture


def _fake_rgb_bytes(width: int, height: int) -> bytes:
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8).tobytes()


@pytest.fixture
def mock_mss():
    with patch("src.perception.screen_capture.mss.MSS") as mock_mss_cls:
        sct_instance = MagicMock()
        mock_mss_cls.return_value = sct_instance
        sct_instance.monitors = [
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]

        def grab_side_effect(monitor=None):
            mock_sct = MagicMock()
            if isinstance(monitor, dict):
                mock_sct.width = monitor["width"]
                mock_sct.height = monitor["height"]
            elif isinstance(monitor, int) and monitor > 0:
                mock_sct.width = 1920
                mock_sct.height = 1080
            else:
                mock_sct.width = 1920
                mock_sct.height = 1080
            mock_sct.rgb = _fake_rgb_bytes(mock_sct.width, mock_sct.height)
            return mock_sct

        sct_instance.grab.side_effect = grab_side_effect
        yield mock_mss_cls


@pytest.mark.asyncio
async def test_capture_returns_bytes(mock_mss):
    capture = ScreenCapture(monitor=1)
    result = await capture.capture()
    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_capture_region_returns_bytes(mock_mss):
    capture = ScreenCapture(monitor=1)
    result = await capture.capture_region(10, 10, 200, 100)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_get_screen_size(mock_mss):
    capture = ScreenCapture(monitor=1)
    width, height = capture.get_screen_size()
    assert width == 1920
    assert height == 1080
