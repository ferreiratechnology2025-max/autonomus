from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.execution.action_executor import ActionExecutor
from src.execution.atomic_action import AtomicAction, AtomicActionContext


@pytest.fixture
def mock_executor():
    with patch("src.execution.atomic_action.ActionExecutor") as mock:
        inst = MagicMock(spec=ActionExecutor)
        inst.click = AsyncMock(return_value=True)
        inst.press_hotkey = AsyncMock(return_value=True)
        inst.type_text = AsyncMock(return_value=True)
        mock.return_value = inst
        yield inst


@pytest.fixture
def mock_perception():
    m = MagicMock()
    m.capture = AsyncMock(return_value=b"pre_screenshot")
    return m


@pytest.mark.asyncio
async def test_atomic_action_execute_success(mock_executor):
    action = AtomicAction(
        name="click_save",
        execute=lambda: mock_executor.click(100, 200),
    )
    result = await action.execute()
    assert result is True
    mock_executor.click.assert_awaited_once_with(100, 200)


@pytest.mark.asyncio
async def test_atomic_action_with_compensate(mock_executor):
    comp = AsyncMock(return_value=True)
    action = AtomicAction(
        name="click_save",
        execute=lambda: mock_executor.click(100, 200),
        compensate=comp,
    )
    result = await action.compensate()
    assert result is True
    comp.assert_awaited_once()


@pytest.mark.asyncio
async def test_atomic_action_no_compensate():
    action = AtomicAction(name="noop", execute=lambda: True)
    assert action.compensate is None


@pytest.mark.asyncio
async def test_context_commit_success(mock_executor, mock_perception):
    settings = MagicMock()
    settings.enable_compensation = True
    executor = ActionExecutor(settings)

    with patch.object(executor, "click", new_callable=AsyncMock, return_value=True):
        async with AtomicActionContext(mock_perception, executor) as ctx:
            await ctx.add_action(AtomicAction(
                name="click",
                execute=lambda: executor.click(100, 200),
            ))
            success = await ctx.commit()

    assert success is True


@pytest.mark.asyncio
async def test_context_rollback_on_failure(mock_executor, mock_perception):
    compensate_fn = AsyncMock(return_value=True)

    with patch.object(mock_executor, "click", new_callable=AsyncMock) as mock_click:
        mock_click.return_value = True
        settings = MagicMock()
        settings.enable_compensation = True
        executor = ActionExecutor(settings)
        executor.click = mock_click

        async with AtomicActionContext(mock_perception, executor) as ctx:
            await ctx.add_action(AtomicAction(
                name="good_action",
                execute=lambda: executor.click(100, 200),
                compensate=compensate_fn,
            ))
            await ctx.add_action(AtomicAction(
                name="bad_action",
                execute=AsyncMock(return_value=False),
                compensate=compensate_fn,
            ))
            success = await ctx.commit()

    assert success is False
    assert compensate_fn.awaited


@pytest.mark.asyncio
async def test_context_exception_triggers_rollback(mock_executor, mock_perception):
    compensate_fn = AsyncMock(return_value=True)

    with patch.object(mock_executor, "click", new_callable=AsyncMock) as mock_click:
        mock_click.return_value = True
        settings = MagicMock()
        settings.enable_compensation = True
        executor = ActionExecutor(settings)
        executor.click = mock_click

        with pytest.raises(ValueError):
            async with AtomicActionContext(mock_perception, executor) as ctx:
                await ctx.add_action(AtomicAction(
                    name="click",
                    execute=lambda: executor.click(100, 200),
                    compensate=compensate_fn,
                ))
                raise ValueError("test error")

    assert compensate_fn.awaited


@pytest.mark.asyncio
async def test_context_no_rollback_if_disabled(mock_perception):
    settings = MagicMock()
    settings.enable_compensation = False
    executor = ActionExecutor(settings)
    executor.click = AsyncMock(return_value=True)

    compensate_fn = AsyncMock(return_value=True)

    with pytest.raises(ValueError):
        async with AtomicActionContext(mock_perception, executor) as ctx:
            await ctx.add_action(AtomicAction(
                name="click",
                execute=lambda: executor.click(100, 200),
                compensate=compensate_fn,
            ))
            raise ValueError("test error")

    compensate_fn.assert_not_awaited()


@pytest.mark.asyncio
async def test_context_pre_post_state(mock_executor, mock_perception):
    settings = MagicMock()
    settings.enable_compensation = True
    executor = ActionExecutor(settings)
    executor.click = AsyncMock(return_value=True)

    async with AtomicActionContext(mock_perception, executor) as ctx:
        assert ctx.pre_screenshot == b"pre_screenshot"
        await ctx.add_action(AtomicAction(
            name="click",
            execute=lambda: executor.click(100, 200),
        ))
        success = await ctx.commit()
        assert success is True


@pytest.mark.asyncio
async def test_add_action_stores_action(mock_executor, mock_perception):
    settings = MagicMock()
    settings.enable_compensation = True
    executor = ActionExecutor(settings)
    executor.click = AsyncMock(return_value=True)

    async with AtomicActionContext(mock_perception, executor) as ctx:
        action = AtomicAction(name="click", execute=lambda: executor.click(100, 200))
        await ctx.add_action(action)
        assert len(ctx.actions) == 1
        assert ctx.actions[0].name == "click"
