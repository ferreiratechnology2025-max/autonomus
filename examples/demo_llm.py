"""Demonstrates LLM integration with text, screenshot, and fallback."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import load_settings
from src.integration.llm_cache import LLMCache
from src.integration.models import LLMRequest
from src.integration.openrouter_client import OpenRouterClient


async def main():
    settings = load_settings()
    async with LLMCache(settings) as cache:
        async with OpenRouterClient(settings, cache=cache) as client:
            # 1) Text-only
            print("--- Text-only ---")
            resp = await client.complete(LLMRequest(prompt="Say hello in one word"))
            print(f"  [{resp.model_used}] {resp.content}")
            print(f"  tokens={resp.input_tokens}+{resp.output_tokens} cost=${resp.cost_usd:.6f} cached={resp.cached}")

            # 2) With screenshot
            print("--- With screenshot ---")
            try:
                from src.perception.screen_capture import ScreenCapture

                cap = ScreenCapture(monitor=1)
                img = cap.capture()
                resp2 = await client.complete(
                    LLMRequest(
                        prompt="What application windows do you see?",
                        images=[img],
                    )
                )
                print(f"  [{resp2.model_used}] {resp2.content}")
            except Exception as e:
                print(f"  Screenshot failed (expected on headless): {e}")

            # 3) Cache hit
            print("--- Cache repeat (should be cached) ---")
            resp3 = await client.complete(LLMRequest(prompt="Say hello in one word"))
            print(f"  cached={resp3.cached}")

            print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
