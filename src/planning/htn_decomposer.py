import json
from typing import Any, Dict, List, Optional

from loguru import logger

from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter
from src.memory.memory import MemorySystem
from src.planning.htn_cache import HTNPlanCache
from src.planning.models import Task, TaskStatus


PLANNING_SYSTEM_PROMPT = (
    "You are a GUI automation planner. Decompose the goal into a JSON array of action objects. "
    "Each action must have 'action_type' and 'parameters' (dict). "
    "Available action types: click, type_text, press_hotkey, scroll, screenshot, wait, "
    "launch_browser, navigate, browser_click, browser_click_by_text, browser_type, "
    "browser_type_by_placeholder, browser_select, browser_select_by_label, "
    "browser_press_enter, browser_get_page_text, "
    "browser_wait_for_selector, browser_wait_for_load, close_browser. "
    "For dropdowns (<select>), ALWAYS use browser_select (needs 'selector' and 'value') "
    "or browser_select_by_label (needs 'selector' and 'label'). NEVER use browser_type on a select element. "
    "For web actions: navigate needs 'url', browser_type needs 'selector' and 'text'. "
    "Return ONLY valid JSON array."
)


class HTNDecomposer:
    def __init__(
        self,
        model_router: ModelRouter,
        sensitive_detector: SensitiveDataDetector,
        memory: Optional[MemorySystem] = None,
        cache: Optional[HTNPlanCache] = None,
    ) -> None:
        self.model_router = model_router
        self.sensitive_detector = sensitive_detector
        self.memory = memory
        self.cache = cache

        self.compound_methods: Dict[str, Any] = {
            "login": self._decompose_login,
            "search": self._decompose_search,
            "fill_form": self._decompose_fill_form,
            "open_app": self._decompose_open_app,
            "navegar": self._decompose_web_browse,
            "acessar": self._decompose_web_browse,
            "chrome": self._decompose_web_browse,
            "pje": self._decompose_web_browse,
            "consulta pública": self._decompose_web_browse,
            "navegador": self._decompose_web_browse,
        }

    async def decompose(self, goal: str, context: Optional[dict] = None) -> Task:
        goal_lower = goal.lower()

        for method_name, method_fn in self.compound_methods.items():
            if method_name in goal_lower:
                logger.info(f"Matched compound method: {method_name}")
                return await method_fn(goal, context or {})

        similar = await self._find_similar_episode(goal)
        if similar:
            return await self._reuse_pattern(goal, similar)

        return await self._llm_decompose(goal, context or {})

    async def _find_similar_episode(self, goal: str) -> Optional[dict]:
        if not self.memory:
            return None
        try:
            episodes = await self.memory.get_recent_successes(limit=5)
            for ep in episodes:
                stored_goal = getattr(ep, "goal", "")
                if isinstance(stored_goal, str) and self._goal_similar(goal, stored_goal):
                    return {"goal": stored_goal, "actions": getattr(ep, "parameters", {})}
        except Exception as e:
            logger.warning(f"_find_similar_episode falhou: {e}")
        return None

    def _goal_similar(self, goal_a: str, goal_b: str) -> bool:
        words_a = set(goal_a.lower().split())
        words_b = set(goal_b.lower().split())
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b)
        return overlap / min(len(words_a), len(words_b)) > 0.5

    async def _reuse_pattern(self, goal: str, episode: dict) -> Task:
        logger.info(f"Reusing pattern from past success: {episode.get('goal', '')}")
        return Task(
            name=goal,
            description=f"Reused pattern from: {episode.get('goal', '')}",
            subtasks=[
                Task(name="reused_action", action_type="click", parameters={"x": 100, "y": 100}),
            ],
        )

    async def _llm_decompose(self, goal: str, context: dict) -> Task:
        cache_key = f"{goal} {json.dumps(context)}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache HIT: {cache_key[:60]}...")
                subtasks = [self._normalize_web_task(item) for item in cached]
                return Task(
                    name=goal,
                    description=f"Cached plan for: {goal[:60]}",
                    subtasks=subtasks,
                )

        prompt = (
            f"Decompose the following goal into a sequence of GUI automation actions.\n"
            f"Goal: {goal}\n"
            f"Context: {json.dumps(context)}\n\n"
            f"Return a JSON array of action objects with 'action_type' and 'parameters'.\n"
            f"Valid action types: click, type_text, press_hotkey, scroll, screenshot, wait, "
            f"launch_browser, navigate, browser_click, browser_click_by_text, browser_type, "
            f"browser_type_by_placeholder, browser_select, browser_select_by_label, "
            f"browser_press_enter, browser_get_page_text, "
            f"browser_wait_for_selector, browser_wait_for_load, close_browser.\n"
            f"For dropdowns (<select>), use browser_select (needs 'selector' and 'value') "
            f"or browser_select_by_label (needs 'selector' and 'label').\n"
            f"navigate needs 'url'. browser_type needs 'selector' and 'text'. "
            f"browser_type_by_placeholder needs 'placeholder' and 'text'."
        )

        detect_text = f"{goal} {json.dumps(context)}"
        has_sensitive = self.sensitive_detector.has_sensitive_data(detect_text)

        response = await self.model_router.generate(
            prompt=prompt,
            task_type="planning",
            has_sensitive=has_sensitive,
            system_prompt=PLANNING_SYSTEM_PROMPT,
        )

        subtasks = self._parse_llm_response(response.text)
        result = Task(
            name=goal,
            description=f"LLM-decomposed plan for: {goal}",
            subtasks=subtasks,
        )

        if self.cache and result.subtasks:
            actions = [{"action_type": t.action_type, "parameters": t.parameters} for t in result.subtasks]
            self.cache.set(cache_key, actions)

        return result

    def _parse_llm_response(self, content: str) -> List[Task]:
        try:
            data = json.loads(content)
            items = data if isinstance(data, list) else data.get("actions", data.get("steps", []))
            if isinstance(items, list) and items:
                return [self._normalize_web_task(item) for item in items]
        except (json.JSONDecodeError, TypeError, AttributeError):
            logger.warning("Failed to parse LLM response as JSON, using fallback")
        return [Task(name="fallback_action", action_type="click", parameters={"x": 500, "y": 500})]

    @staticmethod
    def _normalize_web_task(item: dict) -> Task:
        at = item.get("action_type", "click")
        params = dict(item.get("parameters", {}))

        # Normaliza launch_browser: "browser" -> "channel"
        if at == "launch_browser":
            browser = params.pop("browser", "chrome")
            params.setdefault("channel", browser.lower())

        # Se click/type_text tem selector, converte para browser_*
        if at == "click" and "selector" in params:
            at = "browser_click"
        elif at == "click" and "text" in params and "selector" not in params:
            at = "browser_click_by_text"
        elif at == "type_text" and "selector" in params:
            text = params.pop("text", "")
            at = "browser_type"
            params.setdefault("text", text)

        # Normaliza wait com selector -> browser_wait_for_selector
        if at == "wait" and "selector" in params:
            at = "browser_wait_for_selector"

        # Normaliza press_hotkey Enter -> browser_press_enter
        if at == "press_hotkey":
            keys = params.get("keys", "")
            if isinstance(keys, str) and keys.lower() == "enter":
                at = "browser_press_enter"

        # Normaliza screenshot apos web -> browser_get_page_text
        if at == "screenshot" and not params:
            at = "browser_get_page_text"

        # Normaliza select/select_option -> browser_select
        if at == "select" and "value" in params:
            at = "browser_select"
        elif at == "select" and "label" in params:
            at = "browser_select_by_label"
        elif at == "select_option":
            at = "browser_select"

        return Task(
            name=at,
            action_type=at,
            parameters=params,
        )

    def _fallback_task(self, goal: str) -> Task:
        return Task(
            name=goal,
            description=f"Fallback plan for: {goal}",
            subtasks=[
                Task(name="fallback_click", action_type="click", parameters={"x": 500, "y": 500}),
            ],
        )

    async def _decompose_login(self, goal: str, context: dict) -> Task:
        return Task(
            name="login",
            description="Realizar autenticacao",
            subtasks=[
                Task(name="type_username", action_type="type_text", parameters={"text": context.get("username", "")}),
                Task(name="type_password", action_type="type_text", parameters={"text": context.get("password", ""), "sensitive": True}),
                Task(name="click_login", action_type="click", parameters={"x": 400, "y": 500}),
            ],
        )

    async def _decompose_search(self, goal: str, context: dict) -> Task:
        return Task(
            name="search",
            description="Realizar busca",
            subtasks=[
                Task(name="click_search_field", action_type="click", parameters={"x": 200, "y": 100}),
                Task(name="type_query", action_type="type_text", parameters={"text": context.get("query", "")}),
                Task(name="press_enter", action_type="press_hotkey", parameters={"keys": ("enter",)}),
            ],
        )

    async def _decompose_fill_form(self, goal: str, context: dict) -> Task:
        fields = context.get("fields", [])
        subtasks = []
        for i, field in enumerate(fields):
            subtasks.append(
                Task(name=f"fill_field_{i}", action_type="type_text", parameters={"text": field.get("value", "")}),
            )
            if i < len(fields) - 1:
                subtasks.append(
                    Task(name=f"next_field_{i}", action_type="press_hotkey", parameters={"keys": ("tab",)}),
                )
        subtasks.append(
            Task(name="submit_form", action_type="click", parameters={"x": 400, "y": 600}),
        )
        return Task(name="fill_form", description="Preencher formulario", subtasks=subtasks)

    async def _decompose_web_browse(self, goal: str, context: dict) -> Task:
        logger.info(f"Decompondo goal de navegacao web via LLM: {goal[:60]}")
        return await self._llm_decompose(goal, context)

    async def _decompose_open_app(self, goal: str, context: dict) -> Task:
        app_name = context.get("app_name", "notepad")
        return Task(
            name="open_app",
            description=f"Abrir {app_name}",
            subtasks=[
                Task(name="press_win", action_type="press_hotkey", parameters={"keys": ("win",)}),
                Task(name="type_app_name", action_type="type_text", parameters={"text": app_name}),
                Task(name="press_enter", action_type="press_hotkey", parameters={"keys": ("enter",)}),
            ],
        )
