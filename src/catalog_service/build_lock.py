"""Build 互斥锁：单飞行 + pending 合并。"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TypeVar

from src.catalog_service.models import BuildResult

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BuildLock:
    """同时最多一个 build；忙时标记 pending，结束后再跑一轮。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._building = False
        self._pending = False
        self._pending_trigger = "pending"
        self._cond = threading.Condition(self._lock)

    @property
    def building(self) -> bool:
        with self._lock:
            return self._building

    def request(self, trigger: str, runner: Callable[[str], BuildResult]) -> tuple[BuildResult | None, bool]:
        """请求一次 build。

        返回 `(result, queued)`：
        - 若立即执行：`(BuildResult, False)`
        - 若已在 build：标记 pending，返回 `(None, True)`
        """
        with self._lock:
            if self._building:
                self._pending = True
                self._pending_trigger = trigger
                logger.info("build busy; queued trigger=%s", trigger)
                return None, True
            self._building = True

        try:
            result = self._run_with_pending(trigger, runner)
            return result, False
        finally:
            with self._lock:
                self._building = False
                self._cond.notify_all()

    def _run_with_pending(
        self,
        trigger: str,
        runner: Callable[[str], BuildResult],
    ) -> BuildResult:
        current_trigger = trigger
        last: BuildResult | None = None
        while True:
            logger.info("build start trigger=%s", current_trigger)
            last = runner(current_trigger)
            with self._lock:
                if not self._pending:
                    return last
                current_trigger = self._pending_trigger
                self._pending = False
                logger.info("build pending replay trigger=%s", current_trigger)
