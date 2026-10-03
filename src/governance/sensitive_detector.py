import re
from typing import List, Optional

from loguru import logger


class SensitiveDataDetector:
    def __init__(self):
        self.patterns = {
            "password": re.compile(r"(?i)(?:password|senha|pwd)\s*[:=]\s*\S+"),
            "email": re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}"),
            "phone": re.compile(r"\(?\d{2,3}\)?[\s-]?\d{4,5}[\s-]?\d{4}"),
            "credit_card": re.compile(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"),
            "ssn": re.compile(r"\d{3}-\d{2}-\d{4}"),
            "api_key": re.compile(r"(?i)(?:api[_-]?key|token|sk-[a-zA-Z0-9]{10,})"),
            "jwt": re.compile(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
            "cpf": re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),
            "cnpj": re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"),
            "cep": re.compile(r"\d{5}-?\d{3}"),
            "rg": re.compile(r"\d{1,2}\.?\d{3}\.?\d{3}-?\d"),
            "cns": re.compile(r"\d{3}\s?\d{4}\s?\d{4}\s?\d{4}"),
            "pis": re.compile(r"\d{3}\.?\d{5}\.?\d{2}-?\d"),
            "processo_juridico": re.compile(r"(?i)(?:n[uú]mero\s+(?:do\s+)?processo|proc\.?|autos\s+n[º°]?)\s*:?\s*[\d\.\-/]{10,}"),
            "cid": re.compile(r"(?i)(?:CID|diagn[óo]stico|c[óo]digo\s+internacional)\s*:?\s*[A-TV-Za-tv-z]\d{2}(?:\.\d)?", ),
            "crm": re.compile(r"(?i)CRM[\s\-]*:?\s*\d{4,6}[\s\-]*[A-Z]{2}"),
            "prontuario": re.compile(r"(?i)(?:prontu[áa]rio|registro\s+m[ée]dico|paciente|hist[óo]rico\s+m[ée]dico)\s*:?\s*[\d\-/]{5,}"),
            "conta_bancaria": re.compile(r"(?i)(?:ag[êe]ncia|conta|cc?[.:]?)\s*[.:]?\s*\d[\d\-]{4,}"),
            "pix": re.compile(r"(?i)(?:pix|chave\s+pix)\s*:?\s*[\w.+-]+@[\w.-]+|\+?\d{10,}|[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}"),
            "cvv": re.compile(r"(?i)(?:cvv|cvc|codigo\s+seguran[çc]a)\s*:?\s*\d{3,4}"),
            "passaporte": re.compile(r"[A-Z]{2}\d{6}"),
            "cnh": re.compile(r"\d{11}"),
            "titulo_eleitor": re.compile(r"\d{4,5}\.?\d{4,5}"),
        }

    def detect(self, text: str) -> List[dict]:
        results: List[dict] = []
        for pattern_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                results.append({
                    "type": pattern_type,
                    "value": match.group(),
                    "position": match.span(),
                })
        return results

    async def detect_in_image(self, image_bytes: bytes) -> List[dict]:
        try:
            from src.perception.ocr import OCRProcessor
            from src.core.config import load_settings
            settings = load_settings()
            ocr = OCRProcessor(settings)
            extracted = await ocr.extract_text(image_bytes)
            return self.detect(extracted)
        except Exception as e:
            logger.warning(f"detect_in_image falhou: {e}")
            return []

    def has_sensitive_data(self, text: str) -> bool:
        return len(self.detect(text)) > 0
