"""Testa qual instancia PJe ainda tem Consulta Publica."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integration.browser_manager import get_browser_manager

INSTANCIAS = [
    ("TJPR", "https://pje.tjpr.jus.br/"),
    ("TRF1", "https://pje.trf1.jus.br/"),
    ("TRF3", "https://pje.trf3.jus.br/"),
    ("TRF4", "https://pje.trf4.jus.br/"),
    ("TST", "https://pje.tst.jus.br/"),
    ("TJAL", "https://pje.tjal.jus.br/"),
    ("TJMS", "https://pje.tjms.jus.br/"),
]

async def test_instance(bm, name, url):
    print(f"\n=== {name}: {url} ===")
    ok = await bm.navigate(url)
    if not ok:
        print(f"  NAVEGACAO FALHOU")
        return
    await bm.wait_for_load(timeout=20000)
    await asyncio.sleep(3)

    text = await bm.get_page_text()
    text_lower = (text or "").lower()

    termos = ["consulta", "p\u00fablic", "acessar", "entrar", "processo"]
    for t in termos:
        if t in text_lower:
            print(f"  [OK] '{t}' encontrado")

    # Tenta achar "consulta publica" como texto
    for termo in ["consulta p\u00fablica", "consulta publica", "consulta"]:
        try:
            r = await bm.click_by_text(termo)
            if r:
                print(f"  [CLICK] '{termo}' funcionou!")
                await asyncio.sleep(3)
                text2 = await bm.get_page_text()
                print(f"  Texto apos click: {text2[:300]}")
                return True
        except Exception:
            pass

    # Tenta achar link com consulta
    for sel in ['a[href*="consulta" i]', 'a[href*="public" i]', 'a[href*="acessar" i]']:
        try:
            r = await bm.click(sel)
            if r:
                print(f"  [CLICK] seletor '{sel}' funcionou!")
                await asyncio.sleep(3)
                text2 = await bm.get_page_text()
                print(f"  Texto apos click: {text2[:300]}")
                return True
        except Exception:
            pass

    print(f"  NENHUM CLIQUE FUNCIONOU")
    return False


async def main():
    bm = get_browser_manager()
    ok = await bm.launch(headless=False, channel="chrome")
    if not ok:
        print("Falha ao lancar browser")
        return

    for name, url in INSTANCIAS:
        try:
            if await test_instance(bm, name, url):
                print(f"\n*** {name} FUNCIONA ***")
                break
        except Exception as e:
            print(f"  Erro: {e}")

    await bm.close()

asyncio.run(main())
