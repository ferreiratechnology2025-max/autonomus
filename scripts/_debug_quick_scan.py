"""Quick scan: dump page text from multiple PJe instances."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

INSTANCIAS = [
    ("TRF1", "https://pje.trf1.jus.br/"),
    ("TRF3", "https://pje.trf3.jus.br/"),
    ("TRF4", "https://pje.trf4.jus.br/"),
    ("TJAL", "https://pje.tjal.jus.br/"),
    ("TJMS", "https://pje.tjms.jus.br/"),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        for name, url in INSTANCIAS:
            print(f"\n=== {name}: {url} ===")
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                text = await page.evaluate("() => document.body.innerText")
                preview = (text or "")[:500]
                print(preview)

                # Procura links
                links = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('a')).map(a => a.textContent.trim() + ' -> ' + a.href).join('\\n')
                """)
                if "consulta" in links.lower() or "public" in links.lower():
                    print("--- LINKS ---")
                    for line in links.split("\\n"):
                        if "consulta" in line.lower() or "public" in line.lower():
                            print(f"  {line[:120]}")
                await page.close()
            except Exception as e:
                print(f"  ERRO: {e}")
        await browser.close()

asyncio.run(main())
