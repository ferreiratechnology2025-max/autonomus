from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.integration.models import LLMRequest
from src.integration.openrouter_client import OpenRouterClient


class MockResponse:
    def __init__(self, status=200, data=None, headers=None):
        self.status = status
        self._data = data or {
            "choices": [{"message": {"content": "Hello world"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "openrouter/optimus-alpha",
        }
        self.headers = headers or {"x-request-cost": "0.0", "x-ai-latency": "100"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self):
        return self._data


@pytest.fixture
def settings():
    return Settings(
        openrouter_api_key="sk-or-v1-test-key",
        openrouter_base_url="https://openrouter.ai/api/v1",
        default_model="openrouter/optimus-alpha",
        llm_timeout_seconds=10,
        llm_max_retries=1,
        enable_llm_cache=False,
    )


@pytest.fixture
def settings_no_key():
    return Settings(openrouter_api_key="")


@pytest.mark.asyncio
async def test_dry_run_mode_when_no_api_key(settings_no_key):
    async with OpenRouterClient(settings_no_key) as client:
        assert client.dry_run is True
        request = LLMRequest(prompt="hello")
        response = await client.complete(request)
        assert response.content != ""
        assert "dry-run" in response.model_used


@pytest.mark.asyncio
async def test_complete_returns_response(settings):
    with patch("src.integration.openrouter_client.aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.post.return_value = MockResponse()
        mock_session.close = AsyncMock()
        mock_session_cls.return_value = mock_session

        async with OpenRouterClient(settings) as client:
            request = LLMRequest(prompt="say hello")
            response = await client.complete(request)

    assert response.content == "Hello world"
    assert response.model_used == "openrouter/optimus-alpha"
    assert response.input_tokens == 10
    assert response.output_tokens == 5
    assert isinstance(response.latency_ms, int)


@pytest.mark.asyncio
async def test_complete_uses_cache(settings):
    from src.integration.llm_cache import LLMCache

    cache = MagicMock(spec=LLMCache)
    cached_response = MagicMock()
    cached_response.content = "Cached reply"
    cached_response.model_used = "cached-model"
    cached_response.input_tokens = 5
    cached_response.output_tokens = 3
    cached_response.cost_usd = 0.0
    cached_response.latency_ms = 1
    cache.get.return_value = cached_response

    settings.enable_llm_cache = True
    with patch("src.integration.openrouter_client.aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.post.return_value = MockResponse()
        mock_session.close = AsyncMock()
        mock_session_cls.return_value = mock_session

        async with OpenRouterClient(settings, cache=cache) as client:
            request = LLMRequest(prompt="test")
            response = await client.complete(request)

    assert response.content == "Cached reply"
    assert response.cached is True


@pytest.mark.asyncio
async def test_complete_fallback_on_failure(settings):
    with patch("src.integration.openrouter_client.aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.post.return_value = MockResponse(data={
            "choices": [{"message": {"content": "Fallback response"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            "model": "anthropic/claude-3-haiku",
        })
        mock_session.close = AsyncMock()
        mock_session_cls.return_value = mock_session

        async with OpenRouterClient(settings) as client:
            request = LLMRequest(prompt="test")
            response = await client.complete(request)

    assert response.content == "Fallback response"


@pytest.mark.asyncio
async def test_complete_http_error_triggers_fallback(settings):
    with patch("src.integration.openrouter_client.aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.post.side_effect = [
            MockResponse(status=429, data={"error": {"message": "rate limited"}}),
            MockResponse(data={
                "choices": [{"message": {"content": "Fallback ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
                "model": "anthropic/claude-3-haiku",
            }),
        ]
        mock_session.close = AsyncMock()
        mock_session_cls.return_value = mock_session

        async with OpenRouterClient(settings) as client:
            request = LLMRequest(prompt="test")
            response = await client.complete(request)

    assert response.content == "Fallback ok"
