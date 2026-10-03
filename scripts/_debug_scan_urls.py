"""Quick scan: try CNJ portal and other PJe URLs."""
import asyncio
from playwright.async_api import async_playwright

URLS = [
    ("PJe CNJ", "https://pje.jus.br/"),
    ("CNJ", "https://www.cnj.jus.br/pje/"),
    ("PJe TRF1 Consulta", "https://pje.trf1.jus.br/consultapublica"),
    ("TJPR Consulta", "https://pje.tjpr.jus.br/"),
    ("Google (controle)", "https://www.google.com"),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        for name, url in URLS:
            print(f"\n=== {name}: {url} ===")
            try:
                page = await browser.new_page()
                r = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                status = r.status if r else "?"
                print(f"  Status: {status}")
                await page.wait_for_timeout(2000)
                title = await page.title()
                print(f"  Title: {title}")
                text = await page.evaluate("() => document.body.innerText")
                preview = (text or "")[:400]
                print(f"  Text: {preview}")
                await page.close()
            except Exception as e:
                print(f"  ERRO: {type(e).__name__}: {e}")
        await browser.close()

asyncio.run(main())
