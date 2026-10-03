"""
Cliente para Ollama (LLM local)
Suporta generate com JSON mode e verificacao de disponibilidade.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp


@dataclass
class OllamaResponse:
    text: str
    model: str
    success: bool
    error: Optional[str] = None


class OllamaClient:
    """Cliente para comunicacao com Ollama API local"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:3b") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._available: Optional[bool] = None

    async def check_availability(self) -> bool:
        """Verifica se o Ollama esta rodando e o modelo esta disponivel"""
        if self._available is not None:
            return self._available

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                    if resp.status != 200:
                        self._available = False
                        return False

                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]

                    model_available = any(self.model in m for m in models)
                    if not model_available:
                        print(f"Modelo {self.model} nao encontrado. Disponiveis: {models}")

                    self._available = model_available
                    return model_available

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Ollama nao disponivel: {e}")
            self._available = False
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 30.0,
        json_mode: bool = False,
    ) -> OllamaResponse:
        """
        Gera texto usando Ollama.

        Args:
            prompt: O prompt para o modelo
            system_prompt: Prompt de sistema opcional
            timeout: Timeout em segundos
            json_mode: Se True, força resposta em JSON e valida
        """
        if not await self.check_availability():
            return OllamaResponse(text="", model=self.model, success=False, error="Ollama nao disponivel")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096 if json_mode else 2048,
            },
        }
        if json_mode:
            payload["format"] = "json"
        if system_prompt:
            payload["system"] = system_prompt

        try:
            timeout_cfg = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                    if resp.status != 200:
                        return OllamaResponse(text="", model=self.model, success=False, error=f"HTTP {resp.status}")
                    data = await resp.json()
                    text = data.get("response", "").strip()

                    if json_mode and text:
                        import json
                        try:
                            json.loads(text)
                        except json.JSONDecodeError:
                            return OllamaResponse(
                                text="",
                                model=self.model,
                                success=False,
                                error="Invalid JSON response",
                            )

                    return OllamaResponse(text=text, model=self.model, success=True)
        except asyncio.TimeoutError:
            return OllamaResponse(text="", model=self.model, success=False, error="Timeout")
        except Exception as e:
            return OllamaResponse(text="", model=self.model, success=False, error=str(e))

    async def list_models(self) -> list[str]:
        """Lista modelos disponiveis no Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
