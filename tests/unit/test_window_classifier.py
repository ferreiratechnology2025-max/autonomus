import pytest

from src.perception.window_classifier import (
    get_validation_strategy,
    get_validation_strategy_described,
)


def test_web_browser_chrome():
    assert get_validation_strategy("Chrome_WidgetWin_1") == "HYBRID"


def test_web_browser_firefox():
    assert get_validation_strategy("MozillaWindowClass") == "HYBRID"


def test_web_browser_edge():
    assert get_validation_strategy("Edge") == "HYBRID"


def test_electron_app():
    assert get_validation_strategy("Chrome_WidgetWin_1") == "HYBRID"


def test_native_notepad():
    assert get_validation_strategy("Notepad") == "UIA_PRIMARY"


def test_native_explorer():
    assert get_validation_strategy("CabinetWClass") == "UIA_PRIMARY"


def test_native_calculator():
    assert get_validation_strategy("CalcFrame") == "UIA_PRIMARY"


def test_unknown_window_type():
    assert get_validation_strategy("SomeRandomApp") == "HYBRID"


def test_empty_window_class():
    assert get_validation_strategy("") == "HYBRID"


def test_none_window_class():
    assert get_validation_strategy("") == "HYBRID"


def test_strategy_described_web():
    result = get_validation_strategy_described("Chrome_WidgetWin_1")
    assert result["strategy"] == "HYBRID"
    assert "Web browser" in result["description"]
    assert result["window_class"] == "Chrome_WidgetWin_1"


def test_strategy_described_native():
    result = get_validation_strategy_described("Notepad")
    assert result["strategy"] == "UIA_PRIMARY"
    assert "Native Win32" in result["description"]


def test_strategy_described_unknown():
    result = get_validation_strategy_described("CustomApp")
    assert result["strategy"] == "HYBRID"
    assert "Unknown window type" in result["description"]
