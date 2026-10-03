"""
Jarvis v3 - Entry point principal
Tenta carregar dashboard Textual; fallback para CLI se indisponivel.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    try:
        from src.cli.dashboard import launch_dashboard
        launch_dashboard()
    except ImportError as e:
        print(f"Dashboard nao disponivel ({e}). Usando modo CLI.")
        from src.main_cli import main_cli
        main_cli()


if __name__ == "__main__":
    main()
