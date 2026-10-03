#!/usr/bin/env python
"""
Fase 11 — Teste sandbox PJe local com dropdown.

Uso:
    python scripts/test_sandbox.py

Pre-requisitos:
    - ollama serve rodando com qwen2.5:3b
    - .env com PRIVACY_MODE=true
    - Chrome instalado
    - playwright chromium instalado
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["PYTHONIOENCODING"] = "utf-8"

from src.core.config import load_settings, clear_settings_cache
from src.core.orchestrator import JarvisOrchestrator
from src.integration.browser_manager import get_browser_manager

PASS = "[OK]"
FAIL = "[FAIL]"

steps: list[dict] = []


def _step(num: int, label: str, ok: bool, detail: str = ""):
    steps.append({"num": num, "label": label, "ok": ok, "detail": detail})
    icon = PASS if ok else FAIL
    line = f"  {icon} Passo {num} ({label})"
    if detail:
        line += f": {detail}"
    print(line)


async def run():
    print()
    print("=" * 60)
    print("  Jarvis v3 — Teste Sandbox PJe (Dropdown)")
    print("=" * 60)
    print(f"  Inicio: {datetime.now().isoformat()}")
    print()

    sandbox_path = Path("examples/pje_sandbox.html").resolve()
    if not sandbox_path.exists():
        print(f"  {FAIL} Sandbox HTML nao encontrado em {sandbox_path}")
        return
    sandbox_url = sandbox_path.as_uri()
    print(f"  Sandbox URL: {sandbox_url}")
    print()

    clear_settings_cache()
    settings = load_settings()
    print(f"  PRIVACY_MODE ......... {settings.privacy_mode}")
    print(f"  Ollama model ......... {settings.ollama_model}")
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
    goal = (
        f'Abra o Chrome, navegue ate {sandbox_url}, '
        f'selecione "Parana" no dropdown de estado usando browser_select_by_label, '
        f'digite o texto "0001234" no campo de processo, '
        f'clique no botao Consultar, '
        f'e extraia o texto exibido para verificar se apareceu "sucesso"'
    )

    print(f"  Goal:\n    {goal}\n")
    print("  Executando...")
    print()

    t0 = time.monotonic()
    plan_id = "?"
    try:
        result = await orch.execute_goal(goal)
        elapsed = time.monotonic() - t0
        plan_id = result.get("plan_id", "?")
        success = result.get("success", False)

        bm = get_browser_manager()
        if bm.is_connected:
            page_text = await bm.get_page_text()
            if page_text:
                has_success = "sucesso" in page_text.lower() or "sucesso" in page_text.lower()
                print(f"\n  [DEBUG] Texto da pagina ({len(page_text)} chars):")
                print(f"    {page_text[:400]}")
                print(f"  [DEBUG] Contem 'sucesso': {has_success}")
                print()

        _step(2, "Executar goal", success, f"{elapsed:.1f}s — plan_id={plan_id}")
    except Exception as e:
        elapsed = time.monotonic() - t0
        _step(2, "Executar goal", False, f"{elapsed:.1f}s — {e}")
        result = {"success": False}

    # ── 3. Finalizacao ────────────────────────────────────────────────────
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
        print(f"  {PASS} Todos os passos concluidos!")

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
    report_path = Path("data/reports/sandbox_test_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Relatorio salvo em: {report_path}")
    print("=" * 60)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(run())
