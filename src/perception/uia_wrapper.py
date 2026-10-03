import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    import uiautomation as auto

    _UIA_AVAILABLE = True
except ImportError:
    _UIA_AVAILABLE = False
    auto = None
    logger.warning("uiautomation not available; UIA wrapper will raise on use")


@dataclass
class UIElement:
    automation_id: str = ""
    name: str = ""
    control_type: str = ""
    class_name: str = ""
    bounding_rect: tuple[int, int, int, int] = (0, 0, 0, 0)
    center: tuple[int, int] = (0, 0)
    is_enabled: bool = True
    is_visible: bool = True
    _native_control: Any = None


SearchPredicate = Callable[["UIElement"], bool]


def _make_async(sync_method):
    @functools.wraps(sync_method)
    async def _wrapper(self, *args, **kwargs):
        return await asyncio.to_thread(sync_method, self, *args, **kwargs)
    _wrapper.__name__ = sync_method.__name__ + "_async"
    return _wrapper


def _ensure_uia() -> None:
    if not _UIA_AVAILABLE:
        msg = "uiautomation package is not installed. Install with: pip install uiautomation"
        raise RuntimeError(msg)


def _native_to_element(native: Any) -> Optional[UIElement]:
    try:
        rect = native.BoundingRectangle
        bounding = (rect.left, rect.top, rect.right, rect.bottom)
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2
        return UIElement(
            automation_id=native.AutomationId or "",
            name=native.Name or "",
            control_type=_control_type_name(native.ControlType),
            class_name=native.ClassName or "",
            bounding_rect=bounding,
            center=(cx, cy),
            is_enabled=native.IsEnabled,
            is_visible=native.IsOffscreen is False,
            _native_control=native,
        )
    except Exception as exc:
        logger.debug("Failed to convert native control: %s", exc)
        return None


def _control_type_name(control_type: Any) -> str:
    mapping = {
        50000: "Window",
        50001: "Pane",
        50002: "Document",
        50020: "Edit",
        50021: "ComboBox",
        50030: "Button",
        50031: "CheckBox",
        50032: "RadioButton",
        50033: "Hyperlink",
        50040: "List",
        50041: "ListItem",
        50042: "Tree",
        50043: "TreeItem",
        50044: "Tab",
        50045: "TabItem",
        50050: "Menu",
        50051: "MenuItem",
        50060: "ToolBar",
        50061: "StatusBar",
        50080: "ScrollBar",
        50100: "Slider",
        50101: "ProgressBar",
    }
    return mapping.get(int(control_type), f"Unknown({control_type})")


class UIAWrapper:
    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout
        self._root = None
        if _UIA_AVAILABLE:
            self._root = auto.GetRootControl()
            logger.info("UIAWrapper initialized with root control")

    def _resolve_predicate(self, by: str, value: str) -> SearchPredicate:
        by = by.lower()
        if by == "automation_id":
            return lambda e: e.automation_id == value
        elif by == "name":
            return lambda e: value.lower() in e.name.lower()
        elif by == "control_type":
            return lambda e: e.control_type.lower() == value.lower()
        elif by == "class_name":
            return lambda e: e.class_name.lower() == value.lower()
        else:
            raise ValueError(f"Unknown search criterion: {by}")

    def find_element(
        self,
        by: str = "automation_id",
        value: str = "",
        timeout: Optional[float] = None,
    ) -> Optional[UIElement]:
        _ensure_uia()
        deadline = time.monotonic() + (timeout or self._timeout)
        predicate = self._resolve_predicate(by, value)

        while time.monotonic() < deadline:
            element = self._find_native(predicate)
            if element is not None:
                return element
            if timeout == 0:
                break

        return None

    find_element_async = _make_async(find_element)

    def _find_native(self, predicate: SearchPredicate) -> Optional[UIElement]:
        _ensure_uia()
        if self._root is None:
            return None

        walker = auto.Walker(
            auto.ControlsTreeWalker(),
            auto.FindMode.FindDescendant,
        )
        for native in walker.Walk(self._root):
            try:
                element = _native_to_element(native)
                if element is not None and predicate(element):
                    return element
            except Exception:
                continue
        return None

    def get_text_from_element(self, element: UIElement) -> str:
        if element._native_control is None:
            return element.name
        _ensure_uia()
        try:
            return element._native_control.Name or ""
        except Exception as exc:
            logger.debug("Failed to get text from element: %s", exc)
            return ""

    get_text_from_element_async = _make_async(get_text_from_element)

    def get_clickable_coordinates(self, element: UIElement) -> tuple[int, int]:
        if element._native_control is None:
            return element.center
        _ensure_uia()
        try:
            rect = element._native_control.BoundingRectangle
            return ((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
        except Exception as exc:
            logger.debug("Failed to get clickable coordinates: %s", exc)
            return element.center

    get_clickable_coordinates_async = _make_async(get_clickable_coordinates)

    def wait_for_element(
        self,
        by: str = "automation_id",
        value: str = "",
        timeout: Optional[float] = None,
    ) -> bool:
        return self.find_element(by, value, timeout) is not None

    wait_for_element_async = _make_async(wait_for_element)

    def get_all_elements(
        self,
        predicate: Optional[SearchPredicate] = None,
    ) -> list[UIElement]:
        _ensure_uia()
        if self._root is None:
            return []

        results: list[UIElement] = []
        walker = auto.Walker(
            auto.ControlsTreeWalker(),
            auto.FindMode.FindDescendant,
        )
        for native in walker.Walk(self._root):
            try:
                element = _native_to_element(native)
                if element is not None:
                    if predicate is None or predicate(element):
                        results.append(element)
            except Exception as exc:
                logger.debug("Failed to process native element in get_all_elements: %s", exc)
                continue
        return results

    get_all_elements_async = _make_async(get_all_elements)

    def get_active_window_class(self) -> str:
        _ensure_uia()
        try:
            active = auto.GetForegroundControl()
            if active is not None:
                return active.ClassName or ""
            return ""
        except Exception as exc:
            logger.debug("Failed to get active window class: %s", exc)
            return ""

    get_active_window_class_async = _make_async(get_active_window_class)

    def get_active_window_hwnd(self):
        _ensure_uia()
        try:
            active = auto.GetForegroundControl()
            if active is not None:
                return active.NativeWindowHandle
            return None
        except Exception as exc:
            logger.debug("Failed to get active window hwnd: %s", exc)
            return None

    get_active_window_hwnd_async = _make_async(get_active_window_hwnd)
