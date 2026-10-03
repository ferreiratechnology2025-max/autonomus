import asyncio
import ctypes
import io
from ctypes import wintypes
from typing import Optional, TYPE_CHECKING

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    cv2 = None

import numpy as np
import pyautogui
from loguru import logger
from PIL import Image

from src.core.approval import ApprovalHandler, ApprovalRequest
from src.core.config import Settings
from src.governance.models import PolicyDecision, RiskLevel
from src.perception.screen_capture import ScreenCapture
from src.perception.uia_wrapper import UIAWrapper

from src.integration.browser_manager import get_browser_manager, BrowserManager

if TYPE_CHECKING:
    from src.governance.calibration_models import CalibrationSignal
    from src.governance.policy_engine import PolicyEngine

_user32 = ctypes.windll.user32

_GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
_GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_GetWindowThreadProcessId.restype = wintypes.DWORD

_HWND_MAX_DEPTH = 25

_DOWNSAMPLE_SIZE = (100, 100)
_MAX_STABILITY_FRAMES = 3


class RaceConditionError(Exception):
    """Levantada quando o HWND da janela muda durante a execucao de um clique."""


class ActionExecutor:
    def __init__(self, config: Settings, uia: Optional[UIAWrapper] = None, approval_handler: Optional[ApprovalHandler] = None) -> None:
        self._config = config
        self._timeout_ms = config.action_timeout_ms
        self._safe_margin = config.safe_click_margin
        self._move_duration = config.mouse_move_duration
        self._type_interval = config.type_interval
        self._screen_size = pyautogui.size()
        pyautogui.PAUSE = 0.1
        self._uia = uia
        self._context_lock = asyncio.Lock()
        self._approval_handler = approval_handler
        self._last_extracted_text = ""

    def _validate_coords(self, x: int, y: int) -> bool:
        max_w, max_h = self._screen_size
        margin = self._safe_margin
        if x < margin or y < margin:
            logger.warning(f"Coords ({x}, {y}) within unsafe margin ({margin})")
            return False
        if x >= max_w - margin or y >= max_h - margin:
            logger.warning(f"Coords ({x}, {y}) outside safe area ({max_w}x{max_h})")
            return False
        return True

    @staticmethod
    def _get_pid(hwnd: int) -> Optional[int]:
        if hwnd <= 0:
            return None
        try:
            pid = wintypes.DWORD()
            tid = _GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if tid == 0:
                return None
            return pid.value
        except Exception as e:
            logger.warning(f"_get_pid({hwnd}) falhou: {e}")
            return None

    @staticmethod
    def _get_foreground_hwnd() -> Optional[int]:
        try:
            return _user32.GetForegroundWindow()
        except Exception as e:
            logger.warning(f"_get_foreground_hwnd() falhou: {e}")
            return None

    @staticmethod
    def _is_child_window(parent_hwnd: int, child_hwnd: int, max_depth: int = 10) -> bool:
        try:
            walk = child_hwnd
            for _ in range(max_depth):
                parent = _user32.GetParent(walk)
                if parent == 0:
                    break
                if parent == parent_hwnd:
                    return True
                walk = parent
        except Exception as e:
            logger.warning(f"_is_child_window({parent_hwnd}, {child_hwnd}) falhou: {e}")
        return False

    @staticmethod
    def _is_hwnd_related(target_hwnd: int, current_hwnd: int) -> bool:
        try:
            walk = current_hwnd
            for _ in range(_HWND_MAX_DEPTH):
                parent = _user32.GetParent(walk)
                if parent == 0:
                    break
                if parent == target_hwnd:
                    return True
                walk = parent
        except Exception as e:
            logger.warning(f"_is_hwnd_related({target_hwnd}, {current_hwnd}) falhou: {e}")

        target_pid = ActionExecutor._get_pid(target_hwnd)
        current_pid = ActionExecutor._get_pid(current_hwnd)
        if target_pid is not None and current_pid is not None:
            from src.core.metrics import get_metrics

            get_metrics().increment("pid_fallback_triggered")
            return target_pid == current_pid
        return False

    async def click_element(self, by: str, value: str) -> bool:
        if self._uia is None:
            logger.error("UIAWrapper not available for click_element")
            return False
        from src.core.metrics import get_metrics

        get_metrics().increment("click_element_total")
        try:
            element = await self._uia.find_element_async(by=by, value=value, timeout=5.0)
            if element is None:
                logger.warning(f"Element not found: {by}={value}")
                return False

            lock_timeout_s = self._config.context_lock_timeout_ms / 1000
            try:
                await asyncio.wait_for(self._context_lock.acquire(), timeout=lock_timeout_s)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Context lock timeout after {self._config.context_lock_timeout_ms}ms "
                    f"for {by}={value}"
                )
                return False

            try:
                target_hwnd = await self._uia.get_active_window_hwnd_async()

                debounce_ms = self._config.uia_click_debounce_ms
                if debounce_ms > 0:
                    await asyncio.sleep(debounce_ms / 1000)

                if self._config.uia_enable_visual_stability_check:
                    stable = await self._wait_for_stable_screen(timeout_ms=300)
                    if not stable:
                        logger.warning("Screen not stable after UIA element found")

                if target_hwnd is not None:
                    current_hwnd = await self._uia.get_active_window_hwnd_async()
                    if current_hwnd != target_hwnd and not self._is_hwnd_related(target_hwnd, current_hwnd):
                        from src.core.metrics import get_metrics

                        get_metrics().increment("context_lock_lost")
                        logger.warning(
                            f"Context lock lost: target hwnd={target_hwnd}, current={current_hwnd}. "
                            f"Skipping click."
                        )
                        return False

                coords = await self._uia.get_clickable_coordinates_async(element)
                return await self.click(coords[0], coords[1])
            finally:
                self._context_lock.release()
        except RuntimeError as e:
            logger.error(f"UIA click_element failed: {e}")
            return False

    async def _wait_for_stable_screen(self, timeout_ms: int = 300) -> bool:
        capture = ScreenCapture(monitor=1)
        prev_frame: Optional[bytes] = None
        interval = max(0.04, timeout_ms / 1000 / _MAX_STABILITY_FRAMES)

        for _ in range(_MAX_STABILITY_FRAMES):
            frame = await capture.capture()
            if prev_frame is not None:
                sim = self._lightweight_similarity(frame, prev_frame)
                if sim > 0.98:
                    return True
            prev_frame = frame
            await asyncio.sleep(interval)

        from src.core.metrics import get_metrics

        get_metrics().increment("visual_stability_false_positives")
        logger.warning("Screen did not stabilize within timeout")
        return False

    def _lightweight_similarity(self, img1_bytes: bytes, img2_bytes: bytes) -> float:
        if not _CV2_AVAILABLE:
            return 1.0
        if not img1_bytes or not img2_bytes:
            return 0.0
        img1 = cv2.imdecode(np.frombuffer(img1_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imdecode(np.frombuffer(img2_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            return 0.0
        small1 = cv2.resize(img1, _DOWNSAMPLE_SIZE, interpolation=cv2.INTER_LINEAR)
        small2 = cv2.resize(img2, _DOWNSAMPLE_SIZE, interpolation=cv2.INTER_LINEAR)
        diff = cv2.absdiff(small1.astype(np.float64), small2.astype(np.float64))
        mae = np.mean(diff)
        return max(0.0, min(1.0, 1.0 - (mae / 255.0)))

    async def _execute_with_timeout(self, name: str, action, *args, **kwargs) -> bool:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(action, *args, **kwargs),
                timeout=self._timeout_ms / 1000,
            )
            logger.info(f"{name}: success")
            return True if result is None else bool(result)
        except asyncio.TimeoutError:
            logger.error(f"{name}: timed out after {self._timeout_ms}ms")
            return False
        except Exception as e:
            logger.error(f"{name}: failed - {e}")
            return False

    async def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        if not self._validate_coords(x, y):
            return False

        hwnd_before = self._get_foreground_hwnd()

        result = await self._execute_with_timeout(
            f"click({x},{y})",
            pyautogui.click,
            x, y, button=button, clicks=clicks,
        )

        # TODO(Future): Substituir sleep fixo por espera adaptativa
        # hwnd_before capturado, aguardar ate hwnd estabilizar
        # ou timeout expirar, em vez de 50ms fixos.
        await asyncio.sleep(0.05)
        hwnd_after = self._get_foreground_hwnd()

        if hwnd_before is not None and hwnd_after is not None and hwnd_before != hwnd_after:
            if not self._is_child_window(hwnd_before, hwnd_after):
                from src.core.metrics import get_metrics
                get_metrics().increment("race_condition_detected")
                raise RaceConditionError(
                    f"HWND mudou durante clique: {hwnd_before} -> {hwnd_after}. "
                    "Possivel Alt+Tab ou clique em janela errada."
                )

        return result

    async def double_click(self, x: int, y: int) -> bool:
        try:
            return await self.click(x, y, clicks=2)
        except RaceConditionError as e:
            logger.warning(f"double_click interrompido por race condition: {e}")
            return False

    async def right_click(self, x: int, y: int) -> bool:
        try:
            return await self.click(x, y, button="right")
        except RaceConditionError as e:
            logger.warning(f"right_click interrompido por race condition: {e}")
            return False

    async def move_to(self, x: int, y: int, duration: Optional[float] = None) -> bool:
        if not self._validate_coords(x, y):
            return False
        dur = duration if duration is not None else self._move_duration
        return await self._execute_with_timeout(
            f"move_to({x},{y})",
            pyautogui.moveTo,
            x, y, duration=dur,
        )

    async def type_text(self, text: str, interval: Optional[float] = None) -> bool:
        inter = interval if interval is not None else self._type_interval
        return await self._execute_with_timeout(
            f"type_text(len={len(text)})",
            pyautogui.write,
            text, interval=inter,
        )

    async def press_hotkey(self, *keys: str) -> bool:
        return await self._execute_with_timeout(
            f"hotkey({'+'.join(keys)})",
            pyautogui.hotkey,
            *keys,
        )

    async def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        if x is not None and y is not None and not self._validate_coords(x, y):
            return False
        return await self._execute_with_timeout(
            f"scroll({amount})",
            pyautogui.scroll,
            amount, x, y,
        )

    async def screenshot(self) -> bytes:
        capture = ScreenCapture(monitor=1)
        return await capture.capture()

    async def execute_with_policy(
        self,
        action_type: str,
        params: dict,
        policy_engine: "PolicyEngine",
        context: dict,
    ) -> tuple[bool, PolicyDecision]:
        decision = await policy_engine.evaluate_action(action_type, params, context)
        if decision == PolicyDecision.BLOCK:
            logger.warning(f"Action blocked: {action_type} {params}")
            return False, decision
        if decision == PolicyDecision.CONFIRM:
            approved = await self._request_user_approval(action_type, params)
            if not approved:
                return False, decision
        result = await self._dispatch(action_type, params)
        return result, decision

    async def execute_with_calibration(
        self,
        action_type: str,
        params: dict,
        policy_engine: "PolicyEngine",
        context: dict,
    ) -> tuple[bool, PolicyDecision, "CalibrationSignal"]:
        decision, signal = await policy_engine.evaluate_action_with_calibration(action_type, params, context)

        if decision == PolicyDecision.BLOCK:
            signal.outcome = "blocked"
            return False, decision, signal

        if decision == PolicyDecision.CONFIRM:
            approved = await self._request_user_approval(action_type, params)
            if not approved:
                signal.outcome = "user_denied"
                signal.user_override = True
                return False, decision, signal

        result = await self._dispatch(action_type, params)
        signal.outcome = "success" if result else "failed"
        return result, decision, signal

    async def _request_user_approval(self, action_type: str, params: dict) -> bool:
        if self._approval_handler is not None:
            target = str(params.get("text", params.get("button_text", params.get("value", str(params)))))
            request = ApprovalRequest(
                action_type=action_type,
                target=target[:80],
                risk_level=self._resolve_risk_level(action_type, params),
                reason=f"Acao {action_type} requer confirmacao",
                context=params,
            )
            return await self._approval_handler.request_approval(request)
        logger.warning(f"User approval required: {action_type} {params} (no handler)")
        return True

    def _resolve_risk_level(self, action_type: str, params: dict) -> RiskLevel:
        destructive = {"delete", "remove", "format", "wipe", "shutdown", "reboot"}
        sensitive_text = {"type_text", "press_hotkey"}
        safe_actions = {"move_to", "scroll", "screenshot", "wait", "navigate", "browser_get_page_text", "browser_wait_for_selector", "browser_wait_for_load"}

        if action_type in destructive:
            return RiskLevel.CRITICAL

        text = (params.get("text") or params.get("keys") or "").lower()
        if action_type in sensitive_text and any(kw in text for kw in {"senha", "password", "token", "api"}):
            return RiskLevel.HIGH

        click_targets = (params.get("button_text") or params.get("value") or params.get("selector") or "").lower()
        if any(kw in click_targets for kw in {"delete", "excluir", "remover", "apagar"}):
            return RiskLevel.HIGH

        if action_type in safe_actions:
            return RiskLevel.SAFE

        return RiskLevel.MEDIUM

    async def _dispatch_browser_get_page_text(self) -> bool:
        bm = get_browser_manager()
        text = await bm.get_page_text()
        if text:
            self._last_extracted_text = text
            from src.core.metrics import get_metrics
            get_metrics().increment("browser_text_extracted")
            logger.info(f"Texto extraido da pagina ({len(text)} chars)")
            return True
        logger.warning("Nenhum texto extraido da pagina")
        return False

    async def _launch_browser(self, headless: bool = False, channel: str = "chrome") -> bool:
        bm = get_browser_manager()
        return await bm.launch(headless=headless, channel=channel)

    async def _navigate(self, url: str) -> bool:
        bm = get_browser_manager()
        return await bm.navigate(url)

    async def _browser_click(self, selector: str) -> bool:
        bm = get_browser_manager()
        return await bm.click(selector)

    async def _browser_click_by_text(self, text: str) -> bool:
        bm = get_browser_manager()
        return await bm.click_by_text(text)

    async def _browser_type(self, selector: str, text: str) -> bool:
        bm = get_browser_manager()
        return await bm.type_text(selector, text)

    async def _browser_type_by_placeholder(self, placeholder: str, text: str) -> bool:
        bm = get_browser_manager()
        return await bm.type_text_by_placeholder(placeholder, text)

    async def _browser_select(self, selector: str, value: str) -> bool:
        bm = get_browser_manager()
        return await bm.select_option(selector, value)

    async def _browser_select_by_label(self, selector: str, label: str) -> bool:
        bm = get_browser_manager()
        return await bm.select_option_by_label(selector, label)

    async def _browser_press_enter(self) -> bool:
        bm = get_browser_manager()
        return await bm.press_enter()

    async def _browser_get_page_text(self) -> Optional[str]:
        bm = get_browser_manager()
        return await bm.get_page_text()

    async def _browser_wait(self, ms: int = 1500) -> bool:
        await asyncio.sleep(ms / 1000)
        return True

    async def _browser_wait_for_selector(self, selector: str) -> bool:
        bm = get_browser_manager()
        return await bm.wait_for_selector(selector)

    async def _browser_wait_for_load(self) -> bool:
        bm = get_browser_manager()
        return await bm.wait_for_load()

    async def _close_browser(self) -> bool:
        bm = get_browser_manager()
        await bm.close()
        return True

    async def _dispatch(self, action_type: str, params: dict) -> bool:
        p = dict(params)

        required_params = {
            "click": ["x", "y"],
            "double_click": ["x", "y"],
            "right_click": ["x", "y"],
            "navigate": ["url"],
            "browser_click": ["selector"],
            "browser_type": ["selector", "text"],
            "browser_select": ["selector", "value"],
            "browser_select_by_label": ["selector", "label"],
            "browser_wait_for_selector": ["selector"],
        }
        missing = [k for k in required_params.get(action_type, []) if k not in p or not p.get(k)]
        if missing:
            logger.error(f"{action_type}: parametros obrigatorios ausentes: {missing}")
            return False

        dispatch: dict = {
            "click": lambda: self.click(**p),
            "double_click": lambda: self.double_click(**p),
            "right_click": lambda: self.right_click(**p),
            "move_to": lambda: self.move_to(**p),
            "type_text": lambda: self.type_text(text=p.get("text", ""), interval=p.get("interval")),
            "press_hotkey": lambda: self.press_hotkey(*p.get("keys", ())),
            "scroll": lambda: self.scroll(**p),
            "click_element": lambda: self.click_element(by=p.get("by", "automation_id"), value=p.get("value", "")),
            "launch_browser": lambda: self._launch_browser(headless=p.get("headless", False), channel=p.get("channel", "chrome")),
            "navigate": lambda: self._navigate(url=p.get("url", "")),
            "browser_click": lambda: self._browser_click(selector=p.get("selector", "")),
            "browser_click_by_text": lambda: self._browser_click_by_text(text=p.get("text", "")),
            "browser_type": lambda: self._browser_type(selector=p.get("selector", ""), text=p.get("text", "")),
            "browser_type_by_placeholder": lambda: self._browser_type_by_placeholder(placeholder=p.get("placeholder", ""), text=p.get("text", "")),
            "browser_select": lambda: self._browser_select(selector=p.get("selector", ""), value=p.get("value", "")),
            "browser_select_by_label": lambda: self._browser_select_by_label(selector=p.get("selector", ""), label=p.get("label", "")),
            "browser_press_enter": lambda: self._browser_press_enter(),
            "browser_get_page_text": lambda: self._dispatch_browser_get_page_text(),
            "browser_wait_for_selector": lambda: self._browser_wait_for_selector(selector=p.get("selector", "")),
            "browser_wait_for_load": lambda: self._browser_wait_for_load(),
            "close_browser": lambda: self._close_browser(),
            "wait": lambda: self._browser_wait(ms=p.get("ms", 1500)),
            "screenshot": lambda: self.screenshot() or True,
        }
        handler = dispatch.get(action_type)
        if handler is None:
            logger.error(f"Unknown action type: {action_type}")
            return False
        return await handler()
