#!/usr/bin/env python
"""
consulta_tjpr — Motor de consulta processual PJe (TJPR e multi-tribunal).

Uso:
    consulta_tjpr <numero_processo>

Saida (stdout):
    JSON com resultado da consulta (consumivel pelo Electron/Node)

Comportamento:
    - Tenta tribunais em sequencia ate encontrar consulta publica
    - Navega, filtra, extrai texto — apenas leitura
    - LatencyTracker registra tempo por passo em data/reports/
    - Progresso em stderr; JSON limpo em stdout
"""

import argparse
import asyncio
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.latency_tracker import LatencyTracker
from src.integration.browser_manager import get_browser_manager
from src.core.config import load_settings, clear_settings_cache


TRIBUNAIS = [
    {
        "nome": "TJPR (Projudi - processos importados)",
        "url": "https://pje.tjpr.jus.br/consultapublica/",
        "selector": "#txtFiltro",
        "tipo": "filtro_client",
    },
    {
        "nome": "TJPB",
        "url": "https://pje.tjpb.jus.br/consultapublica/",
        "selector": None,
        "tipo": "generico",
    },
    {
        "nome": "TJMG",
        "url": "https://pje.tjmg.jus.br/consultapublica/",
        "selector": None,
        "tipo": "generico",
    },
    {
        "nome": "TJMA",
        "url": "https://pje.tjma.jus.br/consultapublica/",
        "selector": None,
        "tipo": "generico",
    },
    {
        "nome": "TJPI",
        "url": "https://pje.tjpi.jus.br/consultapublica/",
        "selector": None,
        "tipo": "generico",
    },
]


def eprint(*args):
    print(*args, file=sys.stderr, flush=True)


async def _tentar_tribunal(bm, tribunal: dict) -> dict:
    nome = tribunal["nome"]
    url = tribunal["url"]
    try:
        ok = await bm.navigate(url)
        if not ok:
            return {"tribunal": nome, "status": "fail", "erro": "navegacao falhou"}
        await bm.wait_for_load(timeout=25000)
        await bm.wait_for_timeout(2000)
        txt = (await bm.get_page_text()) or ""
        if not txt or len(txt.strip()) < 10:
            return {"tribunal": nome, "status": "fail", "erro": "pagina sem texto"}
        health = await bm.check_health()
        current_url = bm._page.url if bm._page else "?"
        return {
            "tribunal": nome,
            "url": current_url,
            "status": "ok",
            "texto_len": len(txt),
            "healthy": health["is_healthy"],
            "tipo": tribunal["tipo"],
        }
    except Exception as e:
        return {"tribunal": nome, "url": url, "status": "fail", "erro": str(e)}


async def _consultar_tjpr(bm, tracker: LatencyTracker, processo_numero: str) -> dict:
    try:
        el = bm._page.locator("#txtFiltro")
        await el.wait_for(timeout=10000)
        tracker.start_step("preencher_filtro_tjpr")
        await el.fill(processo_numero, timeout=5000)
        await bm.wait_for_timeout(1000)
        tracker.finish_step("preencher_filtro_tjpr", status="ok")
        txt = (await bm.get_page_text()) or ""
        tracker.start_step("extrair_resultado_tjpr")
        rows = await bm._page.evaluate("""() => {
            const trs = document.querySelectorAll('#tabelaPjeProjudi tbody tr');
            return Array.from(trs).filter(tr => tr.style.display !== 'none').map(tr =>
                Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim())
            );
        }""")
        tracker.finish_step(
            "extrair_resultado_tjpr",
            status="ok",
            metadata={"rows_found": len(rows), "texto_len": len(txt)},
        )
        return {
            "status": "ok",
            "rows_visiveis": rows[:10],
            "total_rows": len(rows),
            "texto_len": len(txt),
        }
    except Exception as e:
        tracker.finish_step("extrair_resultado_tjpr", status="fail", error=str(e))
        return {"status": "fail", "erro": str(e)}


async def consultar(processo_numero: str) -> dict:
    result = {
        "success": False,
        "processo": processo_numero,
        "timestamp": datetime.now().isoformat(),
        "tribunal": None,
        "detalhes": {},
        "steps": [],
        "report_file": None,
        "total_elapsed_ms": 0,
        "error": None,
    }

    clear_settings_cache()
    _ = load_settings()
    tracker = LatencyTracker(report_dir="data/reports")
    bm = get_browser_manager()
    if not bm.is_available:
        result["error"] = "Playwright nao disponivel"
        return result

    eprint("[consulta_tjpr] Abrindo navegador...")
    tracker.start_step("launch_browser")
    try:
        ok = await bm.launch(headless=False, channel="chrome")
        tracker.finish_step("launch_browser", status="ok" if ok else "fail")
        if not ok:
            result["error"] = "Browser launch failed"
            return result
    except Exception as e:
        tracker.finish_step("launch_browser", status="fail", error=str(e))
        result["error"] = f"Browser: {e}"
        return result

    tribunal_encontrado = None
    for trib in TRIBUNAIS:
        nome = trib["nome"]
        eprint(f"[consulta_tjpr] Tentando {nome}...")
        tracker.start_step(f"tribunal_{trib['url'].split('/')[2]}")
        res = await _tentar_tribunal(bm, trib)
        tracker.finish_step(
            f"tribunal_{trib['url'].split('/')[2]}",
            status=res["status"],
            error=res.get("erro"),
            metadata={"texto_len": res.get("texto_len", 0), "healthy": res.get("healthy")},
        )
        if res["status"] == "ok":
            tribunal_encontrado = res
            break

    if tribunal_encontrado is None:
        result["error"] = "Nenhum tribunal respondeu"
    else:
        result["tribunal"] = tribunal_encontrado["tribunal"]
        result["detalhes"]["tribunal"] = tribunal_encontrado
        if tribunal_encontrado.get("tipo") == "filtro_client":
            consulta_result = await _consultar_tjpr(bm, tracker, processo_numero)
            result["detalhes"]["consulta"] = consulta_result
        else:
            tracker.start_step("consultar_processo")
            try:
                gen_placeholder = bm._page.get_by_placeholder("Numero do Processo")
                await gen_placeholder.fill(processo_numero, timeout=10000)
                await bm._page.keyboard.press("Enter")
                await bm.wait_for_load(timeout=30000)
                result_text = (await bm.get_page_text()) or ""
                tracker.finish_step(
                    "consultar_processo",
                    status="ok",
                    metadata={"texto_len": len(result_text)},
                )
                result["detalhes"]["consulta"] = {"status": "ok", "texto_len": len(result_text)}
            except Exception as e:
                tracker.finish_step("consultar_processo", status="fail", error=str(e))
                result["detalhes"]["consulta"] = {"status": "fail", "erro": str(e)}

    eprint("[consulta_tjpr] Encerrando...")
    try:
        await bm.close()
    except Exception as e:
        eprint(f"[consulta_tjpr] Erro no encerramento: {e}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = tracker.save_report(f"consulta_tjpr_{ts}.json")
    result["report_file"] = str(report_path)
    result["total_elapsed_ms"] = tracker.total_elapsed_ms

    for s in tracker._steps:
        step_entry = {
            "name": s.name,
            "status": s.status,
            "elapsed_ms": s.elapsed_ms,
        }
        if s.error:
            step_entry["error"] = s.error
        if s.metadata:
            step_entry["metadata"] = s.metadata
        result["steps"].append(step_entry)

    result["success"] = result["error"] is None
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consulta processual PJe")
    parser.add_argument("processo", help="Numero do processo (formato: NNNNNNN-NN.NNNN.N.NN.NNNN)")
    args = parser.parse_args()

    if not args.processo:
        print("Erro: numero do processo obrigatorio", file=sys.stderr)
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    try:
        result = asyncio.run(consultar(args.processo))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["success"] else 1)
    except Exception as e:
        error_result = {
            "success": False,
            "processo": args.processo,
            "timestamp": datetime.now().isoformat(),
            "error": f"Unhandled exception: {e}",
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
