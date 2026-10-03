import asyncio
import io
from typing import Any

import cv2
import numpy as np
from loguru import logger
from PIL import Image


class UIDetector:
    def __init__(self) -> None:
        pass

    async def find_buttons_by_color(self, image_bytes: bytes) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._find_buttons_sync, image_bytes)

    async def find_input_fields(self, image_bytes: bytes) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._find_inputs_sync, image_bytes)

    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        image = Image.open(io.BytesIO(image_bytes))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def _find_buttons_sync(self, image_bytes: bytes) -> list[dict[str, Any]]:
        img = self._load_image(image_bytes)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        results: list[dict[str, Any]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            aspect_ratio = w / h if h > 0 else 0

            if area > 500 and 1.5 < aspect_ratio < 6:
                results.append({
                    "bbox": [int(x), int(y), int(x + w), int(y + h)],
                    "center": [int(x + w / 2), int(y + h / 2)],
                    "width": int(w),
                    "height": int(h),
                    "type": "button_candidate",
                })

        logger.debug(f"UIDetector found {len(results)} button candidates")
        return results

    def _find_inputs_sync(self, image_bytes: bytes) -> list[dict[str, Any]]:
        img = self._load_image(image_bytes)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        eroded = cv2.erode(dilated, kernel, iterations=1)

        contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        results: list[dict[str, Any]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            aspect_ratio = w / h if h > 0 else 0

            if area > 500 and 1.5 < aspect_ratio < 10:
                results.append({
                    "bbox": [int(x), int(y), int(x + w), int(y + h)],
                    "center": [int(x + w / 2), int(y + h / 2)],
                    "width": int(w),
                    "height": int(h),
                    "type": "input_candidate",
                })

        logger.debug(f"UIDetector found {len(results)} input field candidates")
        return results
