import pytest

from src.core.config import Settings
from src.integration.model_router import ModelRouter


@pytest.fixture
def router():
    settings = Settings(
        default_model="openrouter/optimus-alpha",
        fallback_model_fast="anthropic/claude-3-haiku",
        fallback_model_accurate="anthropic/claude-3.5-sonnet",
    )
    return ModelRouter(settings)


def test_estimate_tokens_text_only(router):
    tokens = router.estimate_tokens("hello world")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_estimate_tokens_with_images(router):
    tokens = router.estimate_tokens("hello", num_images=2)
    assert tokens > 2000


def test_estimate_tokens_empty_text(router):
    tokens = router.estimate_tokens("")
    assert tokens == 0


@pytest.mark.asyncio
async def test_route_sensitive_returns_local(router):
    model = await router.route(None, has_sensitive_data=True)
    assert model == "ollama/local"


@pytest.mark.asyncio
async def test_route_large_context_uses_default_model(router):
    model = await router.route(None, estimated_tokens=100000, has_sensitive_data=False)
    assert model == router.config.default_model


@pytest.mark.asyncio
async def test_route_small_context_uses_fallback(router):
    model = await router.route(None, estimated_tokens=100, has_sensitive_data=False)
    assert model == router.config.fallback_model_fast


@pytest.mark.asyncio
async def test_generate_returns_hybrid_response(router):
    resp = await router.generate("hello", task_type="simple", has_sensitive=False)
    assert hasattr(resp, "text")
    assert hasattr(resp, "model_used")
    assert hasattr(resp, "cost")
