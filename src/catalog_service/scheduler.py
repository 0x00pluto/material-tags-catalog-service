"""定时全量 rebuild（asyncio interval）。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class IntervalScheduler:
    def __init__(
        self,
        interval_sec: float,
        on_tick: Callable[[], None],
    ) -> None:
        self._interval_sec = max(1.0, interval_sec)
        self._on_tick = on_tick
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="catalog-scheduler")
        logger.info("scheduler started interval_sec=%s", self._interval_sec)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("scheduler stopped")

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval_sec)
                break
            except asyncio.TimeoutError:
                pass
            if self._stop.is_set():
                break
            logger.info("scheduler tick")
            try:
                await asyncio.to_thread(self._on_tick)
            except Exception:  # noqa: BLE001
                logger.exception("scheduled rebuild failed")
