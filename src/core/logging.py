import sys
from pathlib import Path

from loguru import logger

from src.core.config import Settings


def setup_logging(settings: Settings) -> None:
    logger.remove()

    log_dir = Path(settings.data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "jarvis_{time}.log"

    is_debug = settings.log_level == "DEBUG"

    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<level>{time:HH:mm:ss} | {level:<7} | {name}:{function}:{line} | {message}</level>",
        colorize=True,
    )

    logger.add(
        log_file,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="7 days",
        compression="gz",
    )
