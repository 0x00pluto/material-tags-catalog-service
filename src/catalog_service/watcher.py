"""watchdog 监听 + debounce。"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.catalog_service.models import SUFFIX

logger = logging.getLogger(__name__)


def _is_tags_event(path: str) -> bool:
    name = Path(path).name
    return name.endswith(SUFFIX)


class _DebouncedTagsHandler(FileSystemEventHandler):
    def __init__(self, debounce_sec: float, on_change: Callable[[], None]) -> None:
        super().__init__()
        self._debounce_sec = debounce_sec
        self._on_change = on_change
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_sec, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        logger.info("watch debounce fired")
        try:
            self._on_change()
        except Exception:  # noqa: BLE001
            logger.exception("watch rebuild failed")

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if _is_tags_event(str(event.src_path)):
            self._schedule()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if _is_tags_event(str(event.src_path)):
            self._schedule()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if _is_tags_event(str(event.src_path)):
            self._schedule()

    def on_moved(self, event: FileSystemEvent) -> None:
        src = str(getattr(event, "src_path", ""))
        dest = str(getattr(event, "dest_path", ""))
        if _is_tags_event(src) or _is_tags_event(dest):
            self._schedule()

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class CatalogWatcher:
    def __init__(
        self,
        root: Path,
        *,
        debounce_sec: float,
        on_change: Callable[[], None],
    ) -> None:
        self._root = root
        self._handler = _DebouncedTagsHandler(debounce_sec, on_change)
        self._observer = Observer()

    def start(self) -> None:
        self._observer.schedule(self._handler, str(self._root), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        logger.info("watcher started root=%s", self._root)

    def stop(self) -> None:
        self._handler.cancel()
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("watcher stopped")
