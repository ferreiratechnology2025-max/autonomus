import asyncio
import json
import time
import uuid
from typing import Optional

import aiohttp
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import Settings
from src.integration.llm_cache import LLMCache
from src.integration.model_router import ModelRouter
from src.integration.models import LLMRequest, LLMResponse


class OpenRouterClient:
    def __init__(self, config: Settings, cache: Optional[LLMCache] = None, budget: Optional["CostBudget"] = None) -> None:
        from src.integration.cost_budget import CostBudget

        self.api_key = config.openrouter_api_key
        self.base_url = config.openrouter_base_url
        self.timeout = config.llm_timeout_seconds
        self.request_timeout = config.llm_request_timeout_seconds
        self.max_retries = config.llm_max_retries
        self.cache = cache
        self.router = ModelRouter(config)
        self.dry_run = not bool(self.api_key)
        self._session: aiohttp.ClientSession | None = None
        self._budget = budget or CostBudget(max_daily_budget=config.max_daily_llm_budget)

        if self.dry_run:
            logger.warning("OPENROUTER_API_KEY not set. Running in dry-run mode (mock responses).")

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        from src.core.metrics import get_metrics

        get_metrics().increment("llm_request_count")
        model = await self.router.route(request)

        if self.dry_run:
            return self._dry_run_response(request, model)

        if self.cache:
            prompt_hash = self.cache._hash_prompt(request.prompt, request.system_prompt, model)
            cached = await self.cache.get(prompt_hash)
            if cached:
                get_metrics().increment("llm_cache_hit_count")
                logger.info(f"LLM cache hit for prompt_hash={prompt_hash[:8]}")
                cached.cached = True
                return cached

        if self._budget.is_exhausted():
            get_metrics().increment("llm_budget_exhausted_count")
            logger.warning(f"Daily LLM budget exhausted (${self._budget.budget_remaining():.4f} remaining). "
                          f"Returning budget-exceeded response.")
            return LLMResponse(
                content="",
                model_used="budget_exceeded",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
            )

        response = await self._call_with_fallback(request, model)

        if response.content:
            self._budget.record_cost(response.cost_usd)

        if self.cache and response:
            await self.cache.set(prompt_hash, response)

        return response

    async def _call_with_fallback(self, request: LLMRequest, primary_model: str) -> LLMResponse:
        from src.core.metrics import get_metrics

        models_to_try = [
            primary_model,
            self.router.config.fallback_model_fast,
            self.router.config.fallback_model_accurate,
        ]

        for model in models_to_try:
            try:
                return await self._call_openrouter(request, model)
            except asyncio.TimeoutError:
                get_metrics().increment("llm_timeout_count")
                logger.warning(f"Model {model} timed out after {self.request_timeout}s. Trying fallback...")
                continue
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}. Trying fallback...")
                continue

        logger.error("All models failed")
        return LLMResponse(
            content="",
            model_used="none",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=0,
        )

    async def _call_openrouter(self, request: LLMRequest, model: str) -> LLMResponse:
        if not self._session:
            raise RuntimeError("Client not initialized. Use 'async with'.")

        start = time.time()

        payload = {
            "model": model,
            "messages": [],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.system_prompt:
            payload["messages"].append({"role": "system", "content": request.system_prompt})

        content: list[dict] = [{"type": "text", "text": request.prompt}]

        if request.images:
            import base64

            for img_bytes in request.images:
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

        payload["messages"].append({"role": "user", "content": content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Jarvis v3 Autonomous Agent",
        }

        async with self._session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
        ) as resp:
            data = await resp.json()

            if resp.status != 200:
                error_msg = data.get("error", {}).get("message", str(resp.status))
                raise RuntimeError(f"OpenRouter API error ({resp.status}): {error_msg}")

            elapsed_ms = int((time.time() - start) * 1000)

            choice = data["choices"][0]
            content_text = choice["message"]["content"]
            usage = data.get("usage", {})
            cost_str = resp.headers.get("x-request-cost", "0")
            latency_str = resp.headers.get("x-ai-latency", str(elapsed_ms))

            response = LLMResponse(
                content=content_text,
                model_used=data.get("model", model),
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cost_usd=float(cost_str) if cost_str else 0.0,
                latency_ms=int(latency_str),
            )

            logger.info(
                f"LLM call: model={response.model_used} "
                f"tokens={response.input_tokens}+{response.output_tokens} "
                f"cost=${response.cost_usd:.6f} latency={response.latency_ms}ms"
            )
            return response

    def _dry_run_response(self, request: LLMRequest, model: str) -> LLMResponse:
        logger.info(f"Dry-run LLM: model={model}, prompt_len={len(request.prompt)}")
        return LLMResponse(
            content=f"[Dry-run] Simulated response for: {request.prompt[:50]}...",
            model_used=f"dry-run/{model}",
            input_tokens=len(request.prompt) // 4,
            output_tokens=50,
            cost_usd=0.0,
            latency_ms=0,
            cached=False,
        )
