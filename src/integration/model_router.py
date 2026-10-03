"""
ModelRouter - Roteia requisicoes LLM baseado em sensibilidade e tipo de tarefa.

Regras de roteamento (INVERTIDAS vs plano original):
- Dado sensivel -> SO local (Ollama), NUNCA nuvem
- Modo privacidade -> tudo local
- Nao-sensivel -> nuvem primeiro, local como fallback
"""

from typing import Optional

from loguru import logger

from src.core.config import Settings
from src.integration.hybrid_client import HybridLLMClient, HybridResponse

LARGE_CONTEXT_THRESHOLD = 50000
TOKENS_PER_IMAGE = 1000


class ModelRouter:
    """Roteador de modelos com sensibilidade (local-first)"""

    def __init__(self, config: Settings, openrouter_client=None) -> None:
        self.config = config
        self.hybrid = HybridLLMClient(config, openrouter_client)

    def estimate_tokens(self, text: str, num_images: int = 0) -> int:
        text_tokens = max(0, len(text) // 4)
        image_tokens = num_images * TOKENS_PER_IMAGE
        return text_tokens + image_tokens

    async def generate(
        self,
        prompt: str,
        task_type: str = "simple",
        has_sensitive: bool = False,
        system_prompt: Optional[str] = None,
    ) -> HybridResponse:
        """
        Roteia e gera texto baseado em sensibilidade.

        Args:
            prompt: O prompt para o LLM
            task_type: Tipo de tarefa (simple, planning, repair)
            has_sensitive: Se o prompt contem dados sensiveis
            system_prompt: Prompt de sistema opcional

        Returns:
            HybridResponse com texto gerado e metadata
        """
        if has_sensitive:
            logger.info(f"Roteamento LOCAL (sensivel): task={task_type}")
        elif self.config.privacy_mode:
            logger.info(f"Roteamento LOCAL (privacy_mode): task={task_type}")
        else:
            logger.info(f"Roteamento HIBRIDO: task={task_type}")

        return await self.hybrid.generate(
            prompt=prompt,
            task_type=task_type,
            has_sensitive=has_sensitive,
            system_prompt=system_prompt,
        )

    # Mantido para compatibilidade com codigo existente que chama route()
    async def route(self, request, estimated_tokens: int = 0, has_sensitive_data: bool = False) -> str:
        if has_sensitive_data:
            return "ollama/local"
        if estimated_tokens >= LARGE_CONTEXT_THRESHOLD:
            return self.config.default_model
        return self.config.fallback_model_fast

    async def route_with_policy(self, request, policy_engine) -> str:
        return await self.route(request)
