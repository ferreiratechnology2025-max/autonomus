import asyncio
import signal
from typing import Any, Callable, Optional

from loguru import logger

from src.core.config import Settings
from src.core.orchestrator import JarvisOrchestrator


class JarvisMainLoop:
    def __init__(
        self,
        orchestrator: JarvisOrchestrator,
        config: Settings,
    ) -> None:
        self.orchestrator = orchestrator
        self.config = config
        self.running = False
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=config.task_queue_max_size)
        self.health_check_interval = config.health_check_interval_seconds
        self.metrics_flush_interval = config.metrics_flush_interval_seconds
        self._on_task_complete: Optional[Callable] = None

    async def start(self) -> None:
        self.running = True
        await self.orchestrator.initialize()
        logger.info("Jarvis v3 main loop started")

        tasks = [
            asyncio.create_task(self._process_task_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._signal_handler()),
        ]

        await asyncio.gather(*tasks)

    async def _process_task_loop(self) -> None:
        while self.running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                logger.info(f"Processing task: {task.get('goal', 'unknown')}")
                result = await self.orchestrator.execute_goal(
                    goal=task["goal"],
                    context=task.get("context", {}),
                )
                logger.info(f"Task completed: {result}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task processing error: {e}")

    async def _health_check_loop(self) -> None:
        from src.core.health import HealthChecker

        checker = HealthChecker(self.config)
        while self.running:
            await asyncio.sleep(self.health_check_interval)
            status = checker.get_status()
            if status["status"] != "healthy":
                logger.warning(f"Health check: {status['status']}")
                for name, check in status["checks"].items():
                    if check["status"] != "healthy":
                        logger.warning(f"  {name}: {check['status']}")

    async def _signal_handler(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

    async def stop(self) -> None:
        logger.info("Shutting down Jarvis v3...")
        self.running = False

    def submit_task(self, goal: str, context: Optional[dict] = None) -> None:
        self.task_queue.put_nowait({"goal": goal, "context": context or {}})
