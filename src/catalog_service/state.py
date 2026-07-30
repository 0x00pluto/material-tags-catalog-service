"""上次 build 状态（内存）。"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from src.catalog_service.models import BuildResult


class AppState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_build: dict[str, Any] | None = None

    def record_build(self, result: BuildResult) -> None:
        payload = {
            "trigger": result.trigger,
            "written": result.written,
            "skipped": result.skipped,
            "skipped_no_media": result.skipped_no_media,
            "skipped_invalid": result.skipped_invalid,
            "duration_ms": result.duration_ms,
            "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "errors": list(result.errors),
        }
        with self._lock:
            self._last_build = payload

    def last_build(self) -> dict[str, Any] | None:
        with self._lock:
            if self._last_build is None:
                return None
            return dict(self._last_build)
