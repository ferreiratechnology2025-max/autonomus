"""
Ponto de entrada do Jarvis v3 com dashboard Textual.
Executa o orquestrador em background e o dashboard na thread principal.
"""

import asyncio
import threading
import sys
from pathlib import Path

from loguru import logger

from src.core.approval import ApprovalHandler
from src.cli.dashboard import JarvisDashboard
from src.core.config import load_settings
from src.core.logging import setup_logging
from src.core.orchestrator import JarvisOrchestrator


async def run_orchestrator(approval_handler: ApprovalHandler):
    settings = load_settings()
    setup_logging(settings)

    logger.info("Jarvis v3 iniciando com dashboard...")

    orchestrator = JarvisOrchestrator(settings, approval_handler=approval_handler)
    await orchestrator.initialize()

    health = await orchestrator.health_check()
    logger.info(f"Health check: {health['status']}")

    while True:
        await asyncio.sleep(1)


def main():
    approval_handler = ApprovalHandler()
    dashboard = JarvisDashboard()
    approval_handler.set_dashboard(dashboard)

    loop = asyncio.new_event_loop()

    def run_async():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_orchestrator(approval_handler))

    orch_thread = threading.Thread(target=run_async, daemon=True)
    orch_thread.start()

    dashboard.run()


if __name__ == "__main__":
    main()
