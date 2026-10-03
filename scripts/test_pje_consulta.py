#!/usr/bin/env python
"""
Fase 10 — Teste real: consulta pública no PJe via Jarvis v3.

Uso:
    python scripts/test_pje_consulta.py

Pré-requisitos:
    - ollama serve rodando com qwen2.5:3b
    - .env com PRIVACY_MODE=true
    - Chrome instalado
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_settings, clear_settings_cache
from src.core.orchestrator import JarvisOrchestrator
from src.integration.browser_manager import get_browser_manager

import os
os.environ["PYTHONIOENCODING"] = "utf-8"

PASS = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"

steps: list[dict] = []


def _step(num: int, label: str, ok: bool, detail: str = ""):
    steps.append({"num": num, "label": label, "ok": ok, "detail": detail})
    icon = PASS if ok else FAIL
    line = f"  {icon} Passo {num} ({label})"
    if detail:
        line += f": {detail}"
    print(line)


# ── orquestração ─────────────────────────────────────────────────────────────

async def run():
    print()
    print("=" * 60)
    print("  Jarvis v3 — Teste Real PJe (Consulta Pública)")
    print("=" * 60)
    print(f"  Início: {datetime.now().isoformat()}")
    print()

    # ── 0. Ambiente ──────────────────────────────────────────────────────
    clear_settings_cache()
    settings = load_settings()
    print(f"  PRIVACY_MODE ......... {settings.privacy_mode}")
    print(f"  Ollama model ......... {settings.ollama_model}")
    print(f"  OpenRouter ........... {settings.openrouter_enabled}")
    print()

    # ── 1. Inicializa orquestrador ────────────────────────────────────────
    try:
        orch = JarvisOrchestrator(settings)
        await orch.initialize()
        _step(1, "Inicializar orquestrador", True)
    except Exception as e:
        _step(1, "Inicializar orquestrador", False, str(e))
        _finalize([])
        return

    # ── 2. Tarefa ──────────────────────────────────────────────────────────
    # Usa o portal PJe nacional (pje.jus.br) que está no ar,
    # que lista todos os tribunais e permite navegar até a consulta
    goal = """
        Abra o Google Chrome, acesse o site https://pje.jus.br,
        localize a opção "Paraná" ou "Consulta Pública" na página,
        digite o número de processo "0001234-12.2024.8.16.0000" no campo de busca,
        clique em "Consultar" ou pressione Enter,
        e extraia o texto exibido com a situação atual do processo.
    """

    print(f"  Goal:\n    {goal.strip()}\n")
    print("  Executando... (pode levar alguns minutos)")
    print()

    t0 = time.monotonic()
    plan_id = "?"
    try:
        result = await orch.execute_goal(goal)
        elapsed = time.monotonic() - t0
        plan_id = result.get("plan_id", "?")
        success = result.get("success", False)

        # Se falhou, tenta extrair texto da pagina pra debug
        bm = get_browser_manager()
        if bm.is_connected:
            page_text = await bm.get_page_text()
            if page_text:
                print(f"\n  [DEBUG] Texto capturado da pagina ({len(page_text)} chars):")
                print(f"    {page_text[:600]}")
                print()

        _step(2, "Executar goal", success, f"{elapsed:.1f}s — plan_id={plan_id}")
    except Exception as e:
        elapsed = time.monotonic() - t0
        _step(2, "Executar goal", False, f"{elapsed:.1f}s — {e}")
        result = {"success": False}

    # ── 3. Finalização ────────────────────────────────────────────────────
    try:
        bm = get_browser_manager()
        if bm.is_connected:
            await bm.close()
        await orch.shutdown()
        _step(3, "Shutdown orquestrador", True)
    except Exception as e:
        _step(3, "Shutdown orquestrador", False, str(e))

    _finalize(steps, plan_id)


def _finalize(steps: list[dict], plan_id: str = "?"):
    total = len(steps)
    passed = sum(1 for s in steps if s["ok"])
    failed = total - passed

    print()
    print("-" * 60)
    print(f"  Resumo: {passed}/{total} passos OK")
    print()

    if failed:
        print("  Falhas:")
        for s in steps:
            if not s["ok"]:
                print(f"    {FAIL} Passo {s['num']} — {s['label']}: {s['detail']}")
    else:
        print(f"  {PASS} Todos os passos concluídos com sucesso!")

    print()
    print(f"  Fim: {datetime.now().isoformat()}")
    print("=" * 60)
    print()

    report = {
        "timestamp": datetime.now().isoformat(),
        "plan_id": plan_id,
        "total_steps": total,
        "passed": passed,
        "failed": failed,
        "steps": steps,
        "overall_success": failed == 0,
    }
    report_path = Path("data/reports/pje_test_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Relatório salvo em: {report_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(run())
