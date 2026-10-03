import asyncio
import io
from pathlib import Path

import mss
from loguru import logger
from PIL import Image


class ScreenCapture:
    def __init__(self, monitor: int = 1) -> None:
        self._monitor = monitor
        self._sct = mss.MSS()

    async def capture(self) -> bytes:
        return await asyncio.to_thread(self._capture_sync, self._monitor)

    async def capture_region(self, x: int, y: int, width: int, height: int) -> bytes:
        region = {"left": x, "top": y, "width": width, "height": height}
        return await asyncio.to_thread(self._capture_region_sync, region)

    def get_screen_size(self) -> tuple[int, int]:
        monitor_info = self._sct.monitors[self._monitor]
        return monitor_info["width"], monitor_info["height"]

    def _capture_sync(self, monitor: int) -> bytes:
        sct_img = self._sct.grab(self._sct.monitors[monitor])
        img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        logger.debug(f"Screen captured: {sct_img.width}x{sct_img.height} ({len(data)} bytes)")
        return data

    def _capture_region_sync(self, region: dict) -> bytes:
        sct_img = self._sct.grab(region)
        img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        logger.debug(f"Region captured: {region} ({len(data)} bytes)")
        return data
