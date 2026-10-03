"""Debug: what does the LLM return for a web browsing goal?"""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_settings, clear_settings_cache
from src.governance.sensitive_detector import SensitiveDataDetector
from src.integration.model_router import ModelRouter

clear_settings_cache()
settings = load_settings()
detector = SensitiveDataDetector()
router = ModelRouter(settings, openrouter_client=None)

goal = (
    'Abra o Google Chrome, acesse https://pje.tjpr.jus.br/, '
    'localize e clique no link "Consulta P\u00fablica", '
    'digite o n\u00famero de processo "0001234-12.2024.8.16.0000" no campo de busca, '
    'clique em "Consultar" ou pressione Enter, '
    'e extraia o texto exibido com a situa\u00e7\u00e3o atual do processo.'
)

prompt = (
    'Decompose the following goal into a sequence of GUI automation actions.\n'
    f'Goal: {goal}\n'
    'Context: {}\n\n'
    'Return a JSON array of action objects with \'action_type\' and \'parameters\'.\n'
    'Valid action types: click, type_text, press_hotkey, scroll, screenshot, wait, '
    'launch_browser, navigate, browser_click, browser_click_by_text, browser_type, '
    'browser_type_by_placeholder, browser_press_enter, browser_get_page_text, '
    'browser_wait_for_selector, browser_wait_for_load, close_browser\n'
    'For web actions: navigate needs \'url\', browser_click/browser_type needs \'selector\' (CSS), '
    'browser_click_by_text needs \'text\' (visible text).\n'
    'Return ONLY valid JSON.'
)

system = (
    'You are a GUI automation planner. Decompose the goal into a JSON array of action objects. '
    'Each action must have action_type and parameters. Return ONLY valid JSON.'
)


async def main():
    print("=== LLM PROMPT (first 300 chars) ===")
    print(prompt[:300])
    print()

    result = await router.generate(
        prompt=prompt,
        task_type="planning",
        has_sensitive=True,
        system_prompt=system,
    )

    print("=== LLM RAW RESPONSE ===")
    print(repr(result.text))
    print()

    print("=== PARSE ATTEMPT ===")
    try:
        parsed = json.loads(result.text)
        print("Valid JSON:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"JSON ERROR: {e}")
        print("Text around error:")
        start = max(0, e.pos - 50)
        end = min(len(result.text), e.pos + 50)
        print(repr(result.text[start:end]))


asyncio.run(main())
