"""
diagnose_local_first.py
Verifica se o ambiente esta pronto para executar em modo local-first.
"""
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ESC = "\033["
GREEN = f"{ESC}92m"
YELLOW = f"{ESC}93m"
RED = f"{ESC}91m"
CYAN = f"{ESC}96m"
BOLD = f"{ESC}1m"
RESET = f"{ESC}0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    icon = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{icon}] {name}")
    if detail:
        print(f"         {detail}")


def main():
    print(f"\n{BOLD}{CYAN}=== Diagnostico Local-First Jarvis v3 ==={RESET}\n")

    print(f"{BOLD}1. Ambiente Python{RESET}")
    py_ok = sys.version_info >= (3, 10)
    check("Python 3.10+", py_ok, sys.version.split()[0])

    venv_active = sys.prefix != sys.base_prefix
    check("Venv ativo", venv_active, sys.prefix)

    print(f"\n{BOLD}2. Dependencias core{RESET}")
    pkgs = [
        ("pydantic", "pydantic"),
        ("yaml (PyYAML)", "yaml"),
        ("loguru", "loguru"),
        ("httpx", "httpx"),
        ("pytest", "pytest"),
    ]
    for label, mod in pkgs:
        try:
            importlib.import_module(mod)
            check(label, True)
        except ImportError:
            check(label, False, "pip install")

    print(f"\n{BOLD}3. Integracoes opcionais{RESET}")
    for label, mod in [
        ("Pillow (PIL)", "PIL"),
        ("opencv-python (cv2)", "cv2"),
        ("textual (dashboard)", "textual"),
    ]:
        try:
            importlib.import_module(mod)
            check(label, True)
        except ImportError:
            check(label, False, "opcional — funcionalidade parcial")

    print(f"\n{BOLD}4. Ollama (modo local){RESET}")
    ollama_exe = shutil.which("ollama")
    check("ollama no PATH", ollama_exe is not None)
    if ollama_exe:
        try:
            out = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            models = [
                l.split()[0]
                for l in out.stdout.strip().split("\n")[1:]
                if l.strip()
            ]
            check("ollama list", out.returncode == 0, f"Modelos: {models}")
            check("Modelo default (qwen2.5:3b)", "qwen2.5:3b" in models)
            check("Modelo coder (qwen2.5-coder:3b)", "qwen2.5-coder:3b" in models)
        except FileNotFoundError:
            check("ollama executável", False)
        except subprocess.TimeoutExpired:
            check("ollama list (timeout)", False, "Ollama travado?")
        except Exception as e:
            check("ollama list (erro)", False, str(e))

    print(f"\n{BOLD}5. Configuracao e .env{RESET}")
    env_file = Path(".env")
    check("Arquivo .env existe", env_file.exists())
    if env_file.exists():
        content = env_file.read_text()
        has_key = "OPENROUTER_API_KEY" in content
        check("OPENROUTER_API_KEY no .env", has_key)
        privacy = "privacy_mode=true" in content.lower()
        check("PRIVACY_MODE ativado", privacy)
        if not privacy:
            print("         Dica: PRIVACY_MODE=true força 100% local")

    config_file = Path("config/config.yaml")
    check("config/config.yaml existe", config_file.exists())

    print(f"\n{BOLD}6. Sistema de arquivos{RESET}")
    dirs = ["data", "data/logs", "data/cache"]
    for d in dirs:
        p = Path(d)
        check(f"Diretorio {d}", p.exists() or p.is_dir())

    print(f"\n{BOLD}7. Importacao do codigo fonte{RESET}")
    modules = [
        "src.core.config",
        "src.core.health",
        "src.core.logging",
        "src.core.orchestrator",
        "src.governance.sensitive_detector",
        "src.integration.hybrid_client",
        "src.integration.model_router",
        "src.planning.htn_decomposer",
        "src.planning.repair_engine",
        "src.cli.dashboard",
        "src.main",
    ]
    for mod in modules:
        try:
            importlib.import_module(mod)
            check(mod, True)
        except Exception as e:
            check(mod, False, str(e).split("\n")[0])

    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)
    print(f"\n{BOLD}Resultado: {total - failed}/{total} checks passaram{RESET}")
    if failed:
        print(f"{RED}{failed} falha(s) detectada(s). Corrija antes de executar.{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}Tudo ok! O sistema esta pronto para modo local-first.{RESET}")


if __name__ == "__main__":
    main()
