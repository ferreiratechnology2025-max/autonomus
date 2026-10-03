import logging
from typing import Optional

logger = logging.getLogger(__name__)

WEB_BROWSERS = [
    "Chrome_WidgetWin",
    "MozillaWindowClass",
    "Edge",
    "CefBrowserWindow",
    "IEFrame",
]

ELECTRON_APPS = [
    "Chrome_WidgetWin_1",
    "Qt5152QWindowIcon",
]

NATIVE_WIN32 = [
    "Notepad",
    "CabinetWClass",
    "ExploreWClass",
    "CalcFrame",
    "Notepad++",
    "Progman",
]


def _classify_window(window_class: str) -> str:
    if not window_class:
        return "unknown"
    if any(browser in window_class for browser in WEB_BROWSERS):
        return "web_browser"
    if any(electron in window_class for electron in ELECTRON_APPS):
        return "electron"
    if any(native in window_class for native in NATIVE_WIN32):
        return "native_win32"
    return "unknown"


def get_validation_strategy(window_class: str) -> str:
    kind = _classify_window(window_class)
    if kind == "native_win32":
        return "UIA_PRIMARY"
    if kind == "unknown":
        return "HYBRID"
    return "HYBRID"


_WINDOW_DESCRIPTIONS = {
    "web_browser": "Web browser detected; trying UIA first, falling back to OCR",
    "electron": "Electron app detected; trying UIA first, falling back to OCR",
    "native_win32": "Native Win32 app detected; using UIA as primary validation",
    "unknown": "Unknown window type; trying UIA first, falling back to OCR",
}


def get_validation_strategy_described(window_class: str) -> dict:
    kind = _classify_window(window_class)
    strategy = get_validation_strategy(window_class)
    return {
        "strategy": strategy,
        "description": _WINDOW_DESCRIPTIONS.get(kind, ""),
        "window_class": window_class,
    }
