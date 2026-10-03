import time
from pathlib import Path

import pytest
import pytest_asyncio

from src.integration.llm_cache import LLMCache
from src.integration.models import LLMResponse


@pytest_asyncio.fixture
async def cache(tmp_path):
    c = LLMCache(tmp_path / "llm_cache.db", ttl_seconds=3600)
    await c.initialize()
    yield c
    await c.close()


@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache):
    result = await cache.get("nonexistent_hash")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_and_get(cache):
    response = LLMResponse(
        content="Hello",
        model_used="test-model",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.0,
        latency_ms=100,
    )
    await cache.set("hash123", response)

    cached = await cache.get("hash123")
    assert cached is not None
    assert cached.content == "Hello"
    assert cached.model_used == "test-model"


@pytest.mark.asyncio
async def test_cache_overwrite(cache):
    r1 = LLMResponse(content="v1", model_used="m1", input_tokens=1, output_tokens=1, cost_usd=0.0, latency_ms=10)
    r2 = LLMResponse(content="v2", model_used="m2", input_tokens=1, output_tokens=1, cost_usd=0.0, latency_ms=10)
    await cache.set("same_key", r1)
    await cache.set("same_key", r2)
    cached = await cache.get("same_key")
    assert cached is not None
    assert cached.content == "v2"


@pytest.mark.asyncio
async def test_cache_respects_ttl(tmp_path):
    short_cache = LLMCache(tmp_path / "ttl.db", ttl_seconds=0)
    await short_cache.initialize()
    response = LLMResponse(content="x", model_used="m", input_tokens=1, output_tokens=1, cost_usd=0.0, latency_ms=1)
    await short_cache.set("expired_hash", response)
    await short_cache.clear_expired()
    result = await short_cache.get("expired_hash")
    assert result is None
    await short_cache.close()
