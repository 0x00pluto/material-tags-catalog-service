"""watchdog 监听 + debounce。"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.catalog_service.builder import path_has_excluded_dir_name
from src.catalog_service.config import parse_exclude_dir_names
from src.catalog_service.models import SUFFIX

logger = logging.getLogger(__name__)


def _is_tags_event(path: str) -> bool:
    name = Path(path).name
    return name.endswith(SUFFIX)


class _DebouncedTagsHandler(FileSystemEventHandler):
    def __init__(
        self,
        debounce_sec: float,
        on_change: Callable[[], None],
        *,
        root: Path,
        exclude_dir_names: frozenset[str],
        startup_quiet_sec: float = 0.0,
    ) -> None:
        super().__init__()
        self._debounce_sec = debounce_sec
        self._on_change = on_change
        self._root = root
        self._exclude_dir_names = exclude_dir_names
        self._startup_quiet_sec = startup_quiet_sec
        self._quiet_until: float = 0.0
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def begin_quiet_window(self) -> None:
        """watcher start 时调用：开启启动静默窗。"""
        if self._startup_quiet_sec <= 0:
            self._quiet_until = 0.0
            return
        self._quiet_until = time.monotonic() + self._startup_quiet_sec

    def _in_quiet_window(self) -> bool:
        return self._quiet_until > 0 and time.monotonic() < self._quiet_until

    def _is_relevant_tags_path(self, path: str) -> bool:
        if not _is_tags_event(path):
            return False
        if path_has_excluded_dir_name(path, self._root, self._exclude_dir_names):
            return False
        return True

    def _schedule(self) -> None:
        if self._in_quiet_window():
            return
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
        if self._is_relevant_tags_path(str(event.src_path)):
            self._schedule()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._is_relevant_tags_path(str(event.src_path)):
            self._schedule()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._is_relevant_tags_path(str(event.src_path)):
            self._schedule()

    def on_moved(self, event: FileSystemEvent) -> None:
        src = str(getattr(event, "src_path", ""))
        dest = str(getattr(event, "dest_path", ""))
        if self._is_relevant_tags_path(src) or self._is_relevant_tags_path(dest):
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
        exclude_dir_names: frozenset[str] | Sequence[str] | None = None,
        startup_quiet_sec: float = 10.0,
    ) -> None:
        self._root = root
        self._startup_quiet_sec = startup_quiet_sec
        exclude_set = (
            exclude_dir_names
            if isinstance(exclude_dir_names, frozenset)
            else parse_exclude_dir_names(exclude_dir_names)
        )
        self._handler = _DebouncedTagsHandler(
            debounce_sec,
            on_change,
            root=root,
            exclude_dir_names=exclude_set,
            startup_quiet_sec=startup_quiet_sec,
        )
        self._observer = Observer()

    def start(self) -> None:
        self._handler.begin_quiet_window()
        self._observer.schedule(self._handler, str(self._root), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        logger.info(
            "watcher started root=%s quiet_sec=%s",
            self._root,
            self._startup_quiet_sec,
        )

    def stop(self) -> None:
        self._handler.cancel()
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("watcher stopped")
