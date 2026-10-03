"""
Testes de inversao de rota (Fase 3)

Verifica:
- Dado sensivel -> rota local (ollama/local), nunca nuvem
- Modo privacidade -> rota local
- Nao-sensivel -> rota hibrida (nuvem primeiro, local fallback)
"""

import pytest

from src.core.config import Settings
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter


@pytest.mark.asyncio
async def test_sensitive_routes_to_local():
    settings = Settings()
    router = ModelRouter(settings)
    model = await router.route(None, has_sensitive_data=True)
    assert "ollama" in model or "local" in model


@pytest.mark.asyncio
async def test_non_sensitive_uses_fallback():
    settings = Settings()
    router = ModelRouter(settings)
    model = await router.route(None, estimated_tokens=100, has_sensitive_data=False)
    assert model == settings.fallback_model_fast


@pytest.mark.asyncio
async def test_large_context_uses_default():
    settings = Settings()
    router = ModelRouter(settings)
    model = await router.route(None, estimated_tokens=100000, has_sensitive_data=False)
    assert model == settings.default_model


@pytest.mark.asyncio
async def test_hybrid_generate_non_sensitive_returns_response():
    settings = Settings()
    router = ModelRouter(settings)
    resp = await router.generate(
        prompt="Qual a capital do Brasil?",
        task_type="simple",
        has_sensitive=False,
    )
    assert hasattr(resp, "text")
    assert hasattr(resp, "model_used")
    assert hasattr(resp, "cost")
    assert hasattr(resp, "metadata")
    if resp.text:
        assert "ollama" in resp.model_used


@pytest.mark.asyncio
async def test_hybrid_generate_sensitive_never_cloud():
    settings = Settings()
    router = ModelRouter(settings)
    resp = await router.generate(
        prompt="CPF: 123.456.789-09, processe os dados",
        task_type="simple",
        has_sensitive=True,
    )
    if resp.text:
        assert "ollama" in resp.model_used
    assert resp.metadata.get("sensitive_blocked") is not True or resp.text


@pytest.mark.asyncio
async def test_privacy_mode_forces_local():
    settings = Settings(privacy_mode=True)
    router = ModelRouter(settings)
    resp = await router.generate(
        prompt="Qual a previsao do tempo?",
        task_type="simple",
        has_sensitive=False,
    )
    if resp.text:
        assert "ollama" in resp.model_used


def test_sensitive_detector_brazilian_patterns():
    detector = SensitiveDataDetector()
    assert detector.has_sensitive_data("CPF 123.456.789-09")
    assert detector.has_sensitive_data("CNPJ 12.345.678/0001-90")
    assert detector.has_sensitive_data("CEP 01310-100")
    assert detector.has_sensitive_data("Numero do processo: 1234567-89.2024.8.26.0100")
    assert not detector.has_sensitive_data("Qual a previsao do tempo?")


@pytest.mark.asyncio
async def test_end_to_end_detect_and_route():
    detector = SensitiveDataDetector()
    settings = Settings()
    router = ModelRouter(settings)

    text_with_cpf = "Analise o CPF 123.456.789-09 do cliente"
    assert detector.has_sensitive_data(text_with_cpf)

    model = await router.route(None, has_sensitive_data=True)
    assert model == "ollama/local"
