#!/usr/bin/env python
"""Explora o DOM da pagina de consulta publica do TJPR."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.integration.browser_manager import get_browser_manager

bm = get_browser_manager()

async def explore():
    await bm.launch(headless=False, channel="chrome")
    await bm.navigate("https://pje.tjpr.jus.br/consultapublica/")
    await bm.wait_for_load(timeout=30000)
    await asyncio.sleep(5)

    page = bm._page

    # dump all input/button/select elements
    elements = await page.evaluate("""() => {
        const els = document.querySelectorAll('input, button, select, textarea, a');
        return Array.from(els).map(e => ({
            tag: e.tagName,
            type: e.type || '',
            id: e.id,
            name: e.name,
            placeholder: e.placeholder || '',
            text: (e.textContent || '').trim().slice(0, 80),
            value: e.value || '',
            'aria-label': e.getAttribute('aria-label') || '',
            class: e.className.slice(0, 60),
            visible: e.offsetParent !== null,
            href: e.href || '',
        }));
    }""")

    print(f"\nElementos encontrados: {len(elements)}\n")
    for el in elements:
        print(f"  <{el['tag']}> id={el['id']!r} name={el['name']!r} "
              f"type={el['type']!r} placeholder={el['placeholder']!r} "
              f"text={el['text']!r} visible={el['visible']}")

    print(f"\n--- HTML parcial ---")
    html = await page.evaluate("() => document.body.innerHTML.substring(0, 3000)")
    print(html)

    print(f"\n--- Texto da pagina ---")
    txt = await page.evaluate("() => document.body.innerText")
    print(txt[:2000])

    await bm.close()

asyncio.run(explore())
