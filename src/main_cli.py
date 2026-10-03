import asyncio

from loguru import logger

from src.core.config import load_settings
from src.core.health import HealthChecker
from src.core.logging import setup_logging
from src.core.main_loop import JarvisMainLoop
from src.core.orchestrator import JarvisOrchestrator


async def main() -> None:
    settings = load_settings()
    setup_logging(settings)

    logger.info("Jarvis v3 starting...")

    health = HealthChecker(settings)
    status = health.get_status()
    logger.info(f"Health check: {status['status']}")

    for check_name, check_result in status["checks"].items():
        logger.info(f"  {check_name}: {check_result['status']}")

    if status["status"] == "unhealthy":
        logger.error("System unhealthy. Shutting down.")
        return

    orchestrator = JarvisOrchestrator(settings)
    loop = JarvisMainLoop(orchestrator, settings)
    await loop.start()


def main_cli():
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
