#!/usr/bin/env python
"""Explora mais tribunais com PJe ativo."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.integration.browser_manager import get_browser_manager

bm = get_browser_manager()

TRIBUNAIS = [
    "https://pje.tjmg.jus.br/consultapublica/",
    "https://pje.trf3.jus.br/consultapublica/",
    "https://pje.trt15.jus.br/consultapublica/",
    "https://pje.trt1.jus.br/consultapublica/",
    "https://pje.tjpi.jus.br/consultapublica/",
    "https://pje.tjma.jus.br/consultapublica/",
    "https://pje.tjrs.jus.br/consultapublica/",
]

async def explore():
    await bm.launch(headless=False, channel="chrome")
    for url in TRIBUNAIS:
        print(f"\n{'='*60}")
        print(f"  {url}")
        print(f"{'='*60}")
        try:
            nav_ok = await bm.navigate(url)
            if not nav_ok:
                print(f"  NAVEGACAO FALHOU")
                continue
            await bm.wait_for_load(timeout=20000)
            await asyncio.sleep(3)
            txt = (await bm.get_page_text()) or ""
            print(f"  ({len(txt)} chars)")
            print(f"  {txt[:800]}")
            if txt:
                elements = await bm._page.evaluate("""() =>
                    Array.from(document.querySelectorAll('input, button, select')).map(e => ({
                        tag: e.tagName, id: e.id, name: e.name,
                        placeholder: e.placeholder, type: e.type,
                        text: (e.textContent||'').trim().slice(0,60),
                        visible: e.offsetParent !== null
                    }))
                """)
                for el in elements:
                    if el.get('id') or el.get('placeholder') or el.get('text'):
                        print(f"    <{el['tag']}> id={el['id']!r} placeholder={el['placeholder']!r} text={el['text']!r}")
        except Exception as e:
            print(f"  ERRO: {e}")
    await bm.close()

asyncio.run(explore())
