import pytest

from src.core.config import Settings
from src.execution.action_executor import ActionExecutor


@pytest.mark.slow
@pytest.mark.asyncio
async def test_executor_initializes():
    settings = Settings()
    executor = ActionExecutor(settings)
    assert executor is not None


@pytest.mark.slow
@pytest.mark.asyncio
async def test_get_screen_size():
    settings = Settings()
    executor = ActionExecutor(settings)
    size = executor._screen_size
    assert size[0] > 0
    assert size[1] > 0
