import asyncio
from typing import Optional

from loguru import logger

_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    Browser = None
    Page = None
    PlaywrightTimeout = Exception


DEFAULT_TIMEOUT = 15000
_FALLBACK_TIMEOUT = 5000


_HEALTH_ERROR_SIGNALS = [
    ("error 500", "server_error"),
    ("500 internal", "server_error"),
    ("404 not found", "not_found"),
    ("403 forbidden", "forbidden"),
    ("502 bad gateway", "bad_gateway"),
    ("service unavailable", "service_unavailable"),
    ("connection refused", "connection_refused"),
    ("this site can", "site_unreachable"),
    ("this page isn", "page_unreachable"),
    ("login", "login_redirect"),
    ("sign in", "login_redirect"),
    ("accounts/login", "login_redirect"),
    ("auth/login", "login_redirect"),
    ("/login", "login_redirect"),
    ("/auth", "auth_redirect"),
    ("/error", "error_page"),
    ("/404", "not_found"),
]


class BrowserManager:
    """Gerencia ciclo de vida do browser (Playwright) para automacao web."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    @property
    def is_available(self) -> bool:
        return _PLAYWRIGHT_AVAILABLE

    @property
    def is_connected(self) -> bool:
        return self._page is not None

    async def launch(self, headless: bool = False, channel: str = "chrome") -> bool:
        if not _PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright nao instalado. pip install playwright && playwright install chromium")
            return False
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                channel=channel,
                headless=headless,
                args=["--force-renderer-accessibility"],
            )
            self._page = await self._browser.new_page()
            logger.info(f"Browser lancado (channel={channel}, headless={headless})")
            return True
        except Exception as e:
            logger.error(f"Falha ao lancar browser: {e}")
            self._playwright = None
            self._browser = None
            self._page = None
            return False

    async def navigate(self, url: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            logger.warning("Navegacao ignorada: browser nao conectado")
            return False
        try:
            await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            logger.info(f"Navegado para {url}")
            return True
        except Exception as e:
            logger.error(f"Falha ao navegar para {url}: {e}")
            return False

    async def click(self, selector: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            await self._page.click(selector, timeout=_FALLBACK_TIMEOUT)
            logger.info(f"Click no elemento '{selector}'")
            return True
        except PlaywrightTimeout:
            logger.warning(f"Timeout ao clicar em '{selector}' — tentando fallbacks")
            return await self._fallback_click(selector, timeout)
        except Exception as e:
            logger.error(f"Falha ao clicar em '{selector}': {e}")
            return False

    async def _fallback_click(self, text_or_selector: str, timeout: int) -> bool:
        if not self._page:
            return False
        strategies = [
            ("get_by_text (exact)", lambda: self._page.get_by_text(text_or_selector, exact=True).click(timeout=timeout)),
            ("get_by_text (contains)", lambda: self._page.get_by_text(text_or_selector).first.click(timeout=timeout)),
            ("get_by_role link", lambda: self._page.get_by_role("link", name=text_or_selector).click(timeout=timeout)),
            ("get_by_role button", lambda: self._page.get_by_role("button", name=text_or_selector).click(timeout=timeout)),
            ("css case-insensitive href", lambda: self._page.click(f'[href*="{text_or_selector}" i]', timeout=timeout)),
            ("locator text", lambda: self._page.locator(f"text={text_or_selector}").first.click(timeout=timeout)),
        ]
        for name, fn in strategies:
            try:
                await fn()
                logger.info(f"Fallback click OK: {name}")
                return True
            except Exception as e:
                logger.warning(f"Fallback click '{name}' falhou: {e}", exc_info=False)
        logger.warning(f"Todos fallbacks falharam para '{text_or_selector}'")
        return False

    async def click_by_text(self, text: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        return await self._fallback_click(text, timeout)

    async def type_text(self, selector: str, text: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            try:
                await self._page.fill(selector, text, timeout=_FALLBACK_TIMEOUT)
                logger.info(f"Texto digitado em '{selector}'")
                return True
            except Exception as e:
                logger.warning(f"Fill '{selector}' falhou ({e}), tentando type direto")
                return await self._type_text_fallback(selector, text)
        except Exception as e2:
            logger.error(f"Falha type_text: {e2}")
            return False

    async def _type_text_fallback(self, selector: str, text: str) -> bool:
        if not self._page:
            return False
        try:
            await self._page.type(selector, text, timeout=_FALLBACK_TIMEOUT)
            return True
        except Exception:
            logger.warning("Type tambem falhou, tentando primeiro input visivel")
            return await self._type_text_any_input(text)

    async def _type_text_any_input(self, text: str) -> bool:
        if not self._page:
            return False
        try:
            first_input = self._page.locator(
                "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio])"
            ).first
            await first_input.wait_for(timeout=_FALLBACK_TIMEOUT)
            await first_input.fill(text, timeout=_FALLBACK_TIMEOUT)
            logger.info(f"type_text fallback input OK: {text[:20]}")
            return True
        except Exception as e:
            logger.warning(f"type_text fallback input falhou: {e}")
            return False

    async def type_text_by_placeholder(self, placeholder: str, text: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            el = self._page.get_by_placeholder(placeholder)
            await el.fill(text, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Falha fill por placeholder '{placeholder}': {e}")
            return False

    async def press_enter(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            await self._page.keyboard.press("Enter")
            await self._page.wait_for_timeout(500)
            return True
        except Exception as e:
            logger.error(f"Falha ao pressionar Enter: {e}")
            return False

    async def get_text(self, selector: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
        if not self._page:
            return None
        try:
            el = await self._page.query_selector(selector)
            if el:
                return await el.inner_text(timeout=timeout)
            return None
        except Exception as e:
            logger.error(f"Falha ao obter texto de '{selector}': {e}")
            return None

    async def get_page_text(self) -> Optional[str]:
        if not self._page:
            return None
        try:
            return await self._page.evaluate("() => document.body.innerText")
        except Exception as e:
            logger.error(f"Falha ao obter texto da pagina: {e}")
            return None

    async def select_option(self, selector: str, value: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            await self._page.select_option(selector, value)
            logger.info(f"browser_select: {selector} = {value}")
            return True
        except Exception as e:
            logger.error(f"browser_select failed: {e}")
            return False

    async def select_option_by_label(self, selector: str, label: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            try:
                await self._page.wait_for_selector(selector, timeout=_FALLBACK_TIMEOUT)
                await self._page.select_option(selector, label=label)
                logger.info(f"browser_select_by_label: {selector} = {label}")
                return True
            except Exception as e1:
                logger.warning(f"Seletor '{selector}' falhou ({e1}), tentando fallback generico")
                return await self._select_by_label_fallback(label)
        except Exception as e2:
            logger.error(f"browser_select_by_label failed: {e2}")
            return False

    async def _select_by_label_fallback(self, label: str) -> bool:
        if not self._page:
            return False
        try:
            any_select = self._page.locator("select").first
            await any_select.wait_for(timeout=_FALLBACK_TIMEOUT)
            try:
                await any_select.select_option(label=label)
            except Exception:
                logger.warning(f"Label '{label}' nao encontrado exato, tentando fuzzy JS")
                found = await self._page.evaluate(
                    """(l) => {
                        const sel = document.querySelector('select');
                        if (!sel) return false;
                        const norm = l.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                        for (const opt of sel.options) {
                            const optNorm = opt.text.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                            if (optNorm.includes(norm) || norm.includes(optNorm)) {
                                sel.value = opt.value;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                return true;
                            }
                        }
                        return false;
                    }""",
                    label,
                )
                if not found:
                    raise Exception(f"Opcao '{label}' nao encontrada no select")
            logger.info(f"browser_select_by_label fallback OK: {label}")
            return True
        except Exception as e:
            logger.warning(f"browser_select_by_label fallback falhou: {e}")
            return False

    async def wait_for_timeout(self, ms: int = 1000) -> None:
        if self._page:
            await self._page.wait_for_timeout(ms)

    async def wait_for_selector(self, selector: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if not self._page:
            return False
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"wait_for_selector('{selector}') falhou: {e}")
            return False

    async def wait_for_load(self, timeout: int = 30000) -> bool:
        if not self._page:
            return False
        try:
            await self._page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception:
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=10000)
                return True
            except Exception as e:
                logger.warning(f"wait_for_load (domcontentloaded) falhou: {e}")
                return False

    async def check_health(self) -> dict:
        if not self._page:
            return {"is_healthy": False, "current_url": None, "signals": ["browser_not_connected"]}

        current_url = await self._get_current_url_safe()
        if current_url is None:
            return {"is_healthy": False, "current_url": None, "signals": ["failed_to_get_url"]}

        signals = await self._detect_error_signals(current_url)
        return {
            "is_healthy": len(signals) == 0,
            "current_url": current_url,
            "signals": signals,
        }

    async def _get_current_url_safe(self) -> Optional[str]:
        try:
            return self._page.url
        except Exception as e:
            logger.warning(f"check_health: falha ao ler URL: {e}")
            return None

    async def _detect_error_signals(self, url: str) -> list:
        signals = []
        url_lower = url.lower()
        page_text_lower = ""

        try:
            raw = await self._page.evaluate("() => document.body.innerText.substring(0, 500)")
            page_text_lower = (raw.replace("\n", " ") if raw else "").lower()
        except Exception as e:
            logger.warning(f"check_health: falha ao ler texto da pagina: {e}")

        for signal_text, signal_name in _HEALTH_ERROR_SIGNALS:
            if signal_text in url_lower or signal_text in page_text_lower:
                signals.append(signal_name)

        return signals

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Erro ao fechar browser: {e}")
        finally:
            self._playwright = None
            self._browser = None
            self._page = None
        logger.info("Browser fechado")


_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
