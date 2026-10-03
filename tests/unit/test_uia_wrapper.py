import sys
from unittest.mock import MagicMock, patch

import pytest

from src.perception.uia_wrapper import UIElement, UIAWrapper, _native_to_element, _control_type_name


class FakePoint:
    left = 100
    top = 200
    right = 300
    bottom = 400


class FakeControl:
    AutomationId = "btn_ok"
    Name = "OK Button"
    ControlType = 50030
    ClassName = "Button"
    BoundingRectangle = FakePoint()
    IsEnabled = True
    IsOffscreen = False


class FakeControlNonVisible:
    AutomationId = "btn_hidden"
    Name = "Hidden"
    ControlType = 50030
    ClassName = "Button"
    BoundingRectangle = FakePoint()
    IsEnabled = True
    IsOffscreen = True


def test_native_to_element():
    result = _native_to_element(FakeControl())
    assert result is not None
    assert result.automation_id == "btn_ok"
    assert result.name == "OK Button"
    assert result.control_type == "Button"
    assert result.center == (200, 300)
    assert result.is_enabled is True
    assert result.is_visible is True


def test_native_to_element_width_invalid():
    class BadControl:
        AutomationId = "bad"
        Name = "Bad"
        ControlType = 50000
        ClassName = "Pane"
        BoundingRectangle = None
        IsEnabled = True
        IsOffscreen = False

    result = _native_to_element(BadControl())
    assert result is None


def test_control_type_name_known():
    assert _control_type_name(50030) == "Button"
    assert _control_type_name(50020) == "Edit"
    assert _control_type_name(50000) == "Window"


def test_control_type_name_unknown():
    result = _control_type_name(99999)
    assert "Unknown" in result


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", False)
def test_find_element_raises_without_uia():
    wrapper = UIAWrapper()
    with pytest.raises(RuntimeError, match="uiautomation package is not installed"):
        wrapper.find_element("name", "test")


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_find_element_by_name(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()
    result = wrapper.find_element(by="name", value="OK Button")

    assert result is not None
    assert result.name == "OK Button"


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_find_element_by_automation_id(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()
    result = wrapper.find_element(by="automation_id", value="btn_ok")

    assert result is not None
    assert result.automation_id == "btn_ok"


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_find_element_by_control_type(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()
    result = wrapper.find_element(by="control_type", value="Button")

    assert result is not None
    assert result.control_type == "Button"


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_find_element_not_found(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()
    result = wrapper.find_element(by="name", value="NonExistent", timeout=0)

    assert result is None


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_text_from_element(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    wrapper = UIAWrapper()
    element = UIElement(name="Hello World", _native_control=FakeControl())
    text = wrapper.get_text_from_element(element)
    assert text == "OK Button"


def test_get_text_from_element_no_native():
    wrapper = UIAWrapper()
    element = UIElement(name="Hello")
    text = wrapper.get_text_from_element(element)
    assert text == "Hello"


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_clickable_coordinates(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    wrapper = UIAWrapper()
    element = UIElement(center=(200, 300), _native_control=FakeControl())
    coords = wrapper.get_clickable_coordinates(element)
    assert coords == (200, 300)


def test_get_clickable_coordinates_no_native():
    wrapper = UIAWrapper()
    element = UIElement(center=(200, 300))
    coords = wrapper.get_clickable_coordinates(element)
    assert coords == (200, 300)


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_all_elements(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl(), FakeControlNonVisible()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()
    results = wrapper.get_all_elements()
    assert len(results) == 2


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_all_elements_with_predicate(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl(), FakeControlNonVisible()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()
    results = wrapper.get_all_elements(predicate=lambda e: e.is_visible)
    assert len(results) == 1


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_active_window_class(mock_auto):
    mock_auto.GetForegroundControl.return_value = MagicMock(ClassName="Notepad")
    wrapper = UIAWrapper()
    result = wrapper.get_active_window_class()
    assert result == "Notepad"


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_active_window_class_empty_on_error(mock_auto):
    mock_auto.GetForegroundControl.side_effect = Exception("fail")
    wrapper = UIAWrapper()
    result = wrapper.get_active_window_class()
    assert result == ""


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", False)
def test_get_active_window_class_raises_without_uia():
    wrapper = UIAWrapper()
    with pytest.raises(RuntimeError, match="uiautomation package is not installed"):
        wrapper.get_active_window_class()


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_active_window_class_async(mock_auto):
    mock_auto.GetForegroundControl.return_value = MagicMock(ClassName="Chrome_WidgetWin_1")

    async def run():
        wrapper = UIAWrapper()
        result = await wrapper.get_active_window_class_async()
        assert result == "Chrome_WidgetWin_1"

    import asyncio
    asyncio.run(run())


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_active_window_hwnd(mock_auto):
    mock_control = MagicMock()
    mock_control.NativeWindowHandle = 12345
    mock_auto.GetForegroundControl.return_value = mock_control
    wrapper = UIAWrapper()
    result = wrapper.get_active_window_hwnd()
    assert result == 12345


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_active_window_hwnd_none(mock_auto):
    mock_auto.GetForegroundControl.return_value = None
    wrapper = UIAWrapper()
    result = wrapper.get_active_window_hwnd()
    assert result is None


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
def test_get_active_window_hwnd_async(mock_auto):
    mock_control = MagicMock()
    mock_control.NativeWindowHandle = 67890
    mock_auto.GetForegroundControl.return_value = mock_control

    async def run():
        wrapper = UIAWrapper()
        result = await wrapper.get_active_window_hwnd_async()
        assert result == 67890

    import asyncio
    asyncio.run(run())


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", False)
def test_get_active_window_hwnd_raises_without_uia():
    wrapper = UIAWrapper()
    with pytest.raises(RuntimeError, match="uiautomation package is not installed"):
        wrapper.get_active_window_hwnd()


@patch("src.perception.uia_wrapper._UIA_AVAILABLE", False)
def test_find_element_async_raises_without_uia():
    wrapper = UIAWrapper()

    async def run():
        with pytest.raises(RuntimeError, match="uiautomation package is not installed"):
            await wrapper.find_element_async("name", "test")

    import asyncio
    asyncio.run(run())


@pytest.mark.asyncio
@patch("src.perception.uia_wrapper._UIA_AVAILABLE", True)
@patch("src.perception.uia_wrapper.auto")
async def test_async_methods(mock_auto):
    mock_root = MagicMock()
    mock_auto.GetRootControl.return_value = mock_root

    mock_walker_instance = MagicMock()
    mock_walker_instance.Walk.return_value = [FakeControl()]
    mock_auto.Walker.return_value = mock_walker_instance
    mock_auto.FindMode.FindDescendant = 2
    mock_auto.ControlsTreeWalker = MagicMock()
    mock_auto.ControlsTreeWalker.return_value = MagicMock()

    wrapper = UIAWrapper()

    result = await wrapper.find_element_async(by="name", value="OK Button")
    assert result is not None
    assert result.name == "OK Button"

    wait_result = await wrapper.wait_for_element_async(by="name", value="OK Button")
    assert wait_result is True

    text = await wrapper.get_text_from_element_async(result)
    assert text == "OK Button"
