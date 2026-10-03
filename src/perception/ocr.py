import asyncio
import io
from typing import Any

import cv2
import numpy as np
import pytesseract
from loguru import logger
from PIL import Image

from src.core.config import Settings


class OCRProcessor:
    def __init__(self, config: Settings) -> None:
        self._config = config
        self._tesseract_path = config.tesseract_path
        self._language = config.ocr_language
        self._psm = 6
        self._available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        try:
            pytesseract.pytesseract.tesseract_cmd = self._tesseract_path
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.warning(f"Tesseract not found at '{self._tesseract_path}'. OCR will be unavailable.")
            return False

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary

    async def extract_text(self, image_bytes: bytes) -> str:
        if not self._available:
            return ""
        return await asyncio.to_thread(self._extract_text_sync, image_bytes)

    def _extract_text_sync(self, image_bytes: bytes) -> str:
        image = Image.open(io.BytesIO(image_bytes))
        processed = self._preprocess(image)
        text = pytesseract.image_to_string(processed, lang=self._language, config=f"--psm {self._psm}")
        text = text.strip()
        logger.debug(f"OCR extracted {len(text)} characters")
        return text

    async def extract_text_with_boxes(self, image_bytes: bytes) -> list[dict[str, Any]]:
        if not self._available:
            return []
        return await asyncio.to_thread(self._extract_boxes_sync, image_bytes)

    def _extract_boxes_sync(self, image_bytes: bytes) -> list[dict[str, Any]]:
        image = Image.open(io.BytesIO(image_bytes))
        processed = self._preprocess(image)
        data = pytesseract.image_to_data(
            processed, lang=self._language, config=f"--psm {self._psm}", output_type=pytesseract.Output.DICT
        )

        results: list[dict[str, Any]] = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf > 0:
                results.append({
                    "text": text,
                    "bbox": [data["left"][i], data["top"][i], data["left"][i] + data["width"][i], data["top"][i] + data["height"][i]],
                    "confidence": conf / 100.0,
                })

        logger.debug(f"OCR found {len(results)} text regions")
        return results

    async def find_text(self, image_bytes: bytes, target: str) -> dict[str, Any] | None:
        target_lower = target.lower()
        boxes = await self.extract_text_with_boxes(image_bytes)
        for box in boxes:
            if target_lower in box["text"].lower():
                logger.info(f"Found target '{target}' at {box['bbox']}")
                return box
        logger.debug(f"Target '{target}' not found in OCR output")
        return None
