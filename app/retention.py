# app/retention.py

import asyncio
import logging
from contextlib import suppress
from app.config import RETENTION_YEARS

logger = logging.getLogger(__name__)

class RetentionService:
    """Periodic background worker that will delete old events based on retention policy."""

    def __init__(self, interval_seconds: int | None = None) -> None:
        # If interval_seconds is None, use configured value
        self.interval_seconds = interval_seconds or RETENTION_YEARS
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        """Start the background worker task."""
        if self._task is not None:
            return  # Already started
        logger.info("Starting RetentionService worker...")
        self._task = asyncio.create_task(self._run(), name="retention-worker")

    async def stop(self) -> None:
        """Signal the worker to stop and wait for it to finish."""
        logger.info("Stopping RetentionService worker...")
        self._stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("RetentionService worker stopped.")

    async def _run(self) -> None:
        """Main loop: run retention cycle periodically until stop is requested."""
        logger.info("RetentionService loop started.")
        try:
            while not self._stop.is_set():
                try:
                    # TODO: implement deletion of old events here (safe, idempotent)
                    # For now, just log to prove the loop is alive.
                    logger.debug("Retention cycle tick (placeholder).")
                except Exception:
                    # Never let exceptions kill the loop; log and continue.
                    logger.exception("Retention cycle failed with an exception.")

                # Sleep until next cycle or stop signal
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
                except asyncio.TimeoutError:
                    # Timeout means it's time for the next cycle
                    pass
        finally:
            logger.info("RetentionService loop exiting.")
