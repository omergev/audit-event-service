# app/retention.py

import asyncio
import logging
from contextlib import suppress
from sqlalchemy import text
from app.database import engine
from app.config import (RETENTION_INTERVAL_SECONDS, RETENTION_YEARS, RETENTION_DELETE_LIMIT)
from app.services.events_service import cache_delete_event  # evict cache entries for deleted IDs

logger = logging.getLogger(__name__)

class RetentionService:
    """Periodic background worker that deletes old events based on the retention policy."""

    def __init__(self, interval_seconds: int | None = None) -> None:
        # interval_seconds: how often to run the retention cycle (e.g., every hour)
        self.interval_seconds = interval_seconds or RETENTION_INTERVAL_SECONDS
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        """Start the background worker task."""
        if self._task is not None:
            return  # Already started
        self._stop.clear()
        logger.info(
            "Starting RetentionService worker (interval=%s sec, years=%s)...",
            self.interval_seconds,
            RETENTION_YEARS,
        )
        self._task = asyncio.create_task(self._run(), name="retention-worker")

    async def stop(self) -> None:
        """Signal the worker to stop and wait for it to finish."""
        logger.info("Stopping RetentionService worker...")
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                logger.warning("Retention worker did not stop in time; cancelling...")
                self._task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._task
            finally:
                self._task = None
        logger.info("RetentionService worker stopped.")

    async def _run(self) -> None:
        """Main loop: run retention cycle periodically until stop is requested."""
        logger.info("RetentionService loop started.")
        try:
            while not self._stop.is_set():
                try:
                    deleted_total = await self._retention_cycle()
                    logger.info("Retention cycle finished. Deleted rows: %s", deleted_total)
                except Exception:
                    logger.exception("Retention cycle failed with an exception.")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
                except asyncio.TimeoutError:
                    pass
        finally:
            logger.info("RetentionService loop exiting.")

    async def _retention_cycle(self) -> int:
        """Delete old events in batches until fewer than limit were deleted."""
        return await asyncio.to_thread(self._delete_until_empty)

    def _delete_until_empty(self) -> int:
        """Synchronous part that talks to the DB; runs inside a worker thread."""
        deleted_total = 0
        while True:
            rows = self._delete_one_batch(limit=RETENTION_DELETE_LIMIT)
            deleted_total += rows
            if rows < RETENTION_DELETE_LIMIT:
                break
        return deleted_total

    def _delete_one_batch(self, limit: int) -> int:
        """
        Delete up to `limit` old rows and return the number of rows deleted.
        Also evict those event IDs from the in-process cache.
        Safe for concurrent runs thanks to SKIP LOCKED and batching.
        """
        sql = text(
            """
            WITH victims AS (
                SELECT event_id
                FROM audit_events
                WHERE ingested_at < (NOW() AT TIME ZONE 'UTC') - (:years || ' years')::interval
                ORDER BY ingested_at
                FOR UPDATE SKIP LOCKED
                LIMIT :limit
            )
            DELETE FROM audit_events AS ae
            USING victims
            WHERE ae.event_id = victims.event_id
            RETURNING ae.event_id;
            """
        )
        deleted_ids: list[str] = []
        with engine.begin() as conn:
            result = conn.execute(sql, {"years": str(RETENTION_YEARS), "limit": limit})
            rows = result.fetchall()  # rows contain (event_id,)
            deleted_ids = [r[0] for r in rows]

        # Evict deleted IDs from cache so GET /events/{id} will return 404 immediately.
        for eid in deleted_ids:
            try:
                cache_delete_event(eid)
            except Exception:
                logger.exception("Failed to evict event_id %s from cache", eid)

        logger.info("Retention batch deleted rows: %d", len(deleted_ids))
        return len(deleted_ids)
