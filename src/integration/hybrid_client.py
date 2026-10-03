"""
Cliente LLM Hibrido com roteamento por sensibilidade (INVERTIDO vs plano original)

Regras:
- Dado sensivel (has_sensitive=True) -> SO local, NUNCA nuvem
- Modo privacidade (privacy_mode=True) -> tudo local, nuvem desabilitada
- Nao-sensivel -> nuvem primeiro (mais barato/rapido), local como fallback
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger

from src.core.config import Settings
from src.integration.ollama_client import OllamaClient


@dataclass
class HybridResponse:
    text: str
    model_used: str
    cost: float = 0.0
    cached: bool = False
    metadata: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return bool(self.text) and "degraded" not in self.model_used


class HybridLLMClient:
    """Cliente LLM com roteamento inteligente baseado em sensibilidade"""

    def __init__(self, settings: Settings, openrouter_client=None) -> None:
        self.settings = settings
        self.openrouter = openrouter_client
        self.ollama = OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    async def generate(
        self,
        prompt: str,
        task_type: str = "simple",
        has_sensitive: bool = False,
        system_prompt: Optional[str] = None,
    ) -> HybridResponse:
        """
        Gera texto roteando baseado em sensibilidade.

        Args:
            prompt: O prompt para o LLM
            task_type: Tipo de tarefa (simple, planning, repair)
            has_sensitive: Se o prompt contem dados sensiveis
            system_prompt: Prompt de sistema opcional

        Returns:
            HybridResponse com texto, modelo usado, e metadata
        """
        force_local = self.settings.privacy_mode or has_sensitive
        reason = "privacy_mode" if self.settings.privacy_mode else ("sensitive" if has_sensitive else "none")

        if force_local:
            logger.info(f"Routing to LOCAL (reason={reason}, task={task_type})")
            local = await self._call_ollama(prompt, task_type, system_prompt)
            if local is not None and local.success:
                return HybridResponse(
                    text=local.text,
                    model_used=f"ollama/{local.model}",
                    cost=0.0,
                    metadata={
                        "source": "local",
                        "privacy_mode": self.settings.privacy_mode,
                        "sensitive": has_sensitive,
                    },
                )
            return HybridResponse(
                text="",
                model_used="degraded",
                cost=0.0,
                metadata={
                    "source": "local",
                    "error": "local_unavailable_sensitive_blocked",
                    "sensitive_blocked": has_sensitive,
                },
            )

        logger.info(f"Routing to CLOUD first (task={task_type}, openrouter={self.openrouter is not None}, enabled={self.settings.openrouter_enabled})")

        if self.openrouter is not None and self.settings.openrouter_enabled:
            cloud = await self._call_openrouter(prompt, task_type, system_prompt)
            if cloud is not None and cloud.text:
                return HybridResponse(
                    text=cloud.content,
                    model_used=f"openrouter/{cloud.model_used}",
                    cost=cloud.cost_usd,
                    cached=cloud.cached,
                    metadata={"source": "cloud", "latency_ms": cloud.latency_ms},
                )

        # Fallback local
        local = await self._call_ollama(prompt, task_type, system_prompt)
        if local is not None and local.success:
            return HybridResponse(
                text=local.text,
                model_used=f"ollama/{local.model}",
                cost=0.0,
                metadata={"source": "local", "fallback": True},
            )

        return HybridResponse(
            text="",
            model_used="degraded",
            cost=0.0,
            metadata={"error": "all_backends_unavailable"},
        )

    async def _call_ollama(
        self,
        prompt: str,
        task_type: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[Any]:
        timeout = self.settings.ollama_timeout
        if task_type == "planning":
            timeout = max(timeout, 45.0)
        elif task_type == "repair":
            timeout = max(timeout, 30.0)

        json_mode = task_type in ("planning", "repair")

        for attempt in range(2):
            result = await self.ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                timeout=timeout,
                json_mode=json_mode,
            )
            if result is not None and result.success:
                return result
            await asyncio.sleep(0.5)
        return None

    async def _call_openrouter(
        self,
        prompt: str,
        task_type: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[Any]:
        if self.openrouter is None:
            return None
        try:
            from src.integration.models import LLMRequest

            request = LLMRequest(prompt=prompt, system_prompt=system_prompt)
            return await self.openrouter.complete(request)
        except Exception as e:
            logger.error(f"OpenRouter call failed: {e}")
            return None
