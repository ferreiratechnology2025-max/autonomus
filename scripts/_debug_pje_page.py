"""Debug: captura o texto e screenshot da pagina PJe para entender o layout."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integration.browser_manager import get_browser_manager


async def main():
    bm = get_browser_manager()
    ok = await bm.launch(headless=False, channel="chrome")
    if not ok:
        print("Falha ao lancar browser")
        return

    ok = await bm.navigate("https://pje.tjpr.jus.br/")
    await bm.wait_for_load(timeout=20000)
    await asyncio.sleep(3)

    text = await bm.get_page_text()
    print("=== TEXTO DA PAGINA ===")
    print(text[:3000] if text else "(vazio)")
    print()

    # Lista links e botoes
    page_text_lower = (text or "").lower()
    for term in ["consulta", "p\u00fablic", "consulta p\u00fablica", "acessar", "entrar", "processo", "pje"]:
        if term in page_text_lower:
            print(f"  [ENCONTRADO] '{term}' na pagina")
        else:
            print(f"  [AUSENTE]   '{term}' na pagina")

    print()
    print("=== TENTATIVA DE CLIQUE POR VARIOS SELETORES ===")

    # Tenta diferentes estrategias de clique
    strategies = [
        ("texto exato", lambda: bm.click_by_text("Consulta P\u00fablica")),
        ("texto parcial", lambda: bm.click_by_text("onsulta")),
        ("link texto", lambda: bm.click("a:has-text(\"Consulta\")")),
        ("link href", lambda: bm.click("a[href*=\"consulta\"]")),
        ("qualquer link consulta", lambda: bm.click("[href*=\"consulta\" i]")),
    ]

    for name, fn in strategies:
        print(f"  Tentando {name}...")
        try:
            r = await fn()
            if r:
                print(f"  -> SUCESSO com {name}")
                break
            else:
                print(f"  -> falhou")
        except Exception as e:
            print(f"  -> erro: {e}")

    await asyncio.sleep(3)
    text2 = await bm.get_page_text()
    if text2 and text2 != text:
        print()
        print("=== TEXTO APOS CLIQUE ===")
        print(text2[:2000])

    await bm.close()


asyncio.run(main())
