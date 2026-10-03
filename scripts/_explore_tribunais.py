#!/usr/bin/env python
"""Explora varios tribunais para encontrar consulta publica PJe real."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.integration.browser_manager import get_browser_manager

bm = get_browser_manager()

TRIBUNAIS = [
    "https://pje.trf1.jus.br/consultapublica/",
    "https://pje.tjba.jus.br/consultapublica/",
    "https://pje.tjpb.jus.br/consultapublica/",
    "https://pje-api.tjce.jus.br/consultapublica/",
]

async def explore():
    await bm.launch(headless=False, channel="chrome")
    for url in TRIBUNAIS:
        print(f"\n{'='*60}")
        print(f"  {url}")
        print(f"{'='*60}")
        try:
            await bm.navigate(url)
            await bm.wait_for_load(timeout=25000)
            await asyncio.sleep(4)
            txt = (await bm.get_page_text()) or ""
            print(f"  ({len(txt)} chars): {txt[:500]}")
            elements = await bm._page.evaluate("""() =>
                Array.from(document.querySelectorAll('input, button, select')).map(e => ({
                    tag: e.tagName, id: e.id, name: e.name,
                    placeholder: e.placeholder, type: e.type,
                    text: (e.textContent||'').trim().slice(0,60),
                    visible: e.offsetParent !== null
                }))
            """)
            for el in elements:
                print(f"    <{el['tag']}> id={el['id']!r} name={el['name']!r} "
                      f"placeholder={el['placeholder']!r} text={el['text']!r}")
        except Exception as e:
            print(f"  ERRO: {e}")
    await bm.close()

asyncio.run(explore())
