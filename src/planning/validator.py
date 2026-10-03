import io
from typing import Optional

import cv2
import numpy as np
from loguru import logger
from PIL import Image

from src.perception.ocr import OCRProcessor
from src.perception.screen_capture import ScreenCapture
from src.perception.uia_wrapper import UIAWrapper, UIElement
from src.perception.window_classifier import get_validation_strategy


class Validator:
    def __init__(
        self,
        ocr: Optional[OCRProcessor] = None,
        screen_capture: Optional[ScreenCapture] = None,
        uia: Optional[UIAWrapper] = None,
    ) -> None:
        self.ocr = ocr
        self.screen = screen_capture
        self.uia = uia

    async def _get_window_strategy(self) -> str:
        if self.uia is None:
            return "HYBRID"
        try:
            window_class = await self.uia.get_active_window_class_async()
            strategy = get_validation_strategy(window_class)
            logger.debug(f"Window class '{window_class}' -> strategy '{strategy}'")
            return strategy
        except RuntimeError:
            return "HYBRID"

    async def validate(self, task, pre_screenshot: bytes, post_screenshot: bytes) -> bool:
        if task.postcondition == "text_appeared":
            return await self._validate_text_appeared(task, pre_screenshot, post_screenshot)

        if task.postcondition == "window_changed":
            similarity = self._calculate_similarity(pre_screenshot, post_screenshot)
            result = similarity < 0.7
            logger.debug(f"validate window_changed: similarity={similarity:.3f} -> {result}")
            return result

        if task.postcondition == "element_clicked":
            return True

        return True

    async def _validate_text_appeared(self, task, pre_screenshot: bytes, post_screenshot: bytes) -> bool:
        if self.uia is None and self.ocr is None:
            return True

        strategy = await self._get_window_strategy()
        element_name = getattr(task, "element_name", None) or getattr(task, "expected_text", None)

        if self.uia is not None:
            uia_result = await self._check_text_via_uia(element_name)
            if uia_result is True:
                return True
            if strategy == "UIA_PRIMARY" and uia_result is not None:
                return uia_result

        return await self._check_text_via_ocr(post_screenshot)

    async def _check_text_via_uia(self, element_name: Optional[str]) -> Optional[bool]:
        if self.uia is None or not element_name:
            return None
        try:
            element = await self.uia.find_element_async(by="name", value=element_name, timeout=2.0)
            if element is not None:
                logger.debug(f"validate text_appeared (UIA): found element '{element_name}'")
                return True
            return False
        except RuntimeError:
            logger.debug("UIA not available, falling back to OCR")
            return None

    async def _check_text_via_ocr(self, screenshot: bytes) -> bool:
        if self.ocr is None:
            return True
        text = await self.ocr.extract_text(screenshot)
        result = bool(text.strip())
        logger.debug(f"validate text_appeared (OCR): extracted {len(text)} chars -> {result}")
        return result

    def _calculate_similarity(self, img1_bytes: bytes, img2_bytes: bytes) -> float:
        img1 = np.array(Image.open(io.BytesIO(img1_bytes)).convert("L"), dtype=np.float64)
        img2 = np.array(Image.open(io.BytesIO(img2_bytes)).convert("L"), dtype=np.float64)

        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

        diff = cv2.absdiff(img1, img2)
        mse = np.mean(diff ** 2)
        normalized = max(0.0, min(1.0, 1.0 - (mse / (255.0 ** 2))))
        return normalized
