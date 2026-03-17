"""Batch scheduler — runs registered watchers on configurable intervals.

Each watcher implements the Watcher protocol and is executed as an asyncio
background task alongside the MCP server.
"""

import asyncio
import logging
import time
from typing import Protocol

from shared.batch.config import load_batch_config

logger = logging.getLogger(__name__)


class Watcher(Protocol):
    """Protocol for batch watchers. Implement `name` and `run_once`."""

    @property
    def name(self) -> str: ...

    async def run_once(self) -> None: ...


class BatchScheduler:
    """Manages multiple watchers, each running on its own interval."""

    def __init__(self) -> None:
        self._watchers: list[Watcher] = []
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def register(self, watcher: Watcher) -> None:
        self._watchers.append(watcher)
        logger.info("Registered watcher: %s", watcher.name)

    async def start(self) -> None:
        """Start all registered watchers as background tasks."""
        if self._running:
            return
        self._running = True

        for watcher in self._watchers:
            task = asyncio.create_task(
                self._run_loop(watcher),
                name=f"watcher-{watcher.name}",
            )
            self._tasks.append(task)

        logger.info("Batch scheduler started with %d watcher(s)", len(self._watchers))

    async def stop(self) -> None:
        """Cancel all watcher tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Batch scheduler stopped")

    async def _run_loop(self, watcher: Watcher) -> None:
        """Run a single watcher in a loop, re-reading config each cycle."""
        while self._running:
            config = load_batch_config()
            watcher_config = config.get_watcher(watcher.name)

            if not watcher_config.enabled:
                logger.debug("Watcher %s disabled, sleeping 60s", watcher.name)
                await asyncio.sleep(60)
                continue

            start = time.monotonic()
            try:
                await watcher.run_once()
                elapsed = time.monotonic() - start
                logger.info("Watcher %s completed in %.2fs", watcher.name, elapsed)
            except Exception:
                elapsed = time.monotonic() - start
                logger.exception("Watcher %s failed after %.2fs", watcher.name, elapsed)

            interval = watcher_config.interval_minutes * 60
            logger.debug("Watcher %s sleeping %ds until next cycle", watcher.name, interval)
            await asyncio.sleep(interval)
