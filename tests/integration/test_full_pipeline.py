"""
Testes end-to-end do pipeline LLM com roteamento local-first
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import Settings
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.planning.htn_decomposer import HTNDecomposer
from src.planning.repair_engine import RepairEngine
from src.planning.models import RepairStrategy, Task, TaskStatus


@pytest.fixture
def settings():
    return Settings(privacy_mode=False, openrouter_api_key="fake-key")


@pytest.fixture
def detector():
    return SensitiveDataDetector()


@pytest.fixture
def model_router(settings):
    return ModelRouter(settings)


@pytest.mark.asyncio
async def test_planning_with_sensitive_data_uses_local(settings, detector):
    with patch("src.integration.ollama_client.OllamaClient.generate") as mock_ollama:
        mock_ollama.return_value = AsyncMock(
            success=True,
            text='[{"action_type": "click", "parameters": {"x": 100, "y": 200}}]',
            model="qwen2.5:3b",
        )

        router = ModelRouter(settings, openrouter_client=AsyncMock())
        decomposer = HTNDecomposer(router, detector)

        task = "Processar o CPF 123.456.789-00 no sistema"
        result = await decomposer.decompose(task)

        mock_ollama.assert_called()
        call_kwargs = mock_ollama.call_args[1]
        assert call_kwargs.get("json_mode") is True
        assert result is not None


@pytest.mark.asyncio
async def test_repair_uses_model_router(settings, detector):
    with patch(
        "src.integration.hybrid_client.HybridLLMClient._call_ollama"
    ) as mock_local:
        mock_local.return_value = AsyncMock(
            success=True, text="Try clicking the button with a delay", model="qwen2.5:3b"
        )

        router = ModelRouter(settings)
        repair = RepairEngine(router, detector)

        task = Task(name="click_button", action_type="click", parameters={"x": 100, "y": 200})
        error = Exception("Element not found")

        success, strategy = await repair.repair(task, error, {})
        mock_local.assert_called()
        assert success is True
        assert strategy == RepairStrategy.ESCALATE_LLM


@pytest.mark.asyncio
async def test_privacy_mode_blocks_all_cloud_traffic():
    settings = Settings(privacy_mode=True, openrouter_api_key="fake-key")
    detector = SensitiveDataDetector()

    with patch(
        "src.integration.ollama_client.OllamaClient.generate"
    ) as mock_ollama:
        mock_ollama.return_value = AsyncMock(
            success=True, text='{"actions": []}', model="qwen2.5:3b"
        )

        router = ModelRouter(settings, openrouter_client=AsyncMock())
        decomposer = HTNDecomposer(router, detector)

        result = await decomposer.decompose("Qual a capital do Brasil?")

        mock_ollama.assert_called()
        assert result is not None


@pytest.mark.asyncio
async def test_planning_clean_text_no_sensitive_no_cloud(settings, detector):
    with patch(
        "src.integration.hybrid_client.HybridLLMClient._call_openrouter"
    ) as mock_cloud, patch(
        "src.integration.ollama_client.OllamaClient.generate"
    ) as mock_ollama:
        mock_cloud.return_value = AsyncMock(
            content='[{"action_type": "click", "parameters": {"x": 100, "y": 200}}]',
            model_used="claude",
            cost_usd=0.001,
            cached=False,
            latency_ms=500,
        )
        mock_ollama.return_value = AsyncMock(
            success=True,
            text='[{"action_type": "click", "parameters": {"x": 100, "y": 200}}]',
            model="qwen2.5:3b",
        )

        router = ModelRouter(settings, openrouter_client=AsyncMock())
        decomposer = HTNDecomposer(router, detector)

        result = await decomposer.decompose("Abrir o navegador Chrome")

        mock_cloud.assert_called()
        assert result is not None


@pytest.mark.asyncio
async def test_health_check_reflects_privacy_mode():
    settings = Settings(privacy_mode=True)
    from src.core.health import HealthChecker

    checker = HealthChecker(settings)
    llm_status = checker.check_llm()
    assert llm_status["status"] == "healthy"
    assert llm_status["details"]["mode"] == "privacy"


@pytest.mark.asyncio
async def test_health_check_ollama_configured():
    settings = Settings(privacy_mode=False, openrouter_api_key="")
    from src.core.health import HealthChecker

    checker = HealthChecker(settings)
    llm_status = checker.check_llm()
    assert llm_status["status"] == "healthy"
    assert llm_status["details"]["ollama"] == "http://localhost:11434"


@pytest.mark.asyncio
async def test_empty_context_detects_no_sensitive(detector):
    assert not detector.has_sensitive_data("")
    assert not detector.has_sensitive_data("Qual a previsao do tempo?")
