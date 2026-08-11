"""watcher 排除路径降噪与启动静默窗单测。"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from src.catalog_service.models import tags_filename_for_stem
from src.catalog_service.watcher import _DebouncedTagsHandler


def _handler(
    tmp_path: Path,
    exclude: frozenset[str],
    *,
    startup_quiet_sec: float = 0.0,
) -> tuple[_DebouncedTagsHandler, list[int]]:
    fires: list[int] = []

    def on_change() -> None:
        fires.append(1)

    handler = _DebouncedTagsHandler(
        0.01,
        on_change,
        root=tmp_path,
        exclude_dir_names=exclude,
        startup_quiet_sec=startup_quiet_sec,
    )
    return handler, fires


def _tags_event(tmp_path: Path, rel: str = "ok") -> MagicMock:
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(tmp_path / rel / tags_filename_for_stem("x"))
    return event


def test_watch_ignores_excluded_tags_path(tmp_path: Path) -> None:
    handler, _fires = _handler(tmp_path, frozenset({"000-回收站"}))
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(tmp_path / "000-回收站" / tags_filename_for_stem("x"))

    # 不应 schedule：用 cancel 后 timer 仍为 None 验证
    handler.on_created(event)
    assert handler._timer is None


def test_watch_schedules_non_excluded_tags_path(tmp_path: Path) -> None:
    handler, _fires = _handler(tmp_path, frozenset({"000-回收站"}))
    event = _tags_event(tmp_path)

    handler.on_created(event)
    assert handler._timer is not None
    handler.cancel()


def test_watch_quiet_window_ignores_events(tmp_path: Path) -> None:
    handler, _fires = _handler(
        tmp_path, frozenset(), startup_quiet_sec=10.0
    )
    handler.begin_quiet_window()
    handler.on_created(_tags_event(tmp_path))
    assert handler._timer is None


def test_watch_quiet_window_zero_disables(tmp_path: Path) -> None:
    handler, _fires = _handler(
        tmp_path, frozenset(), startup_quiet_sec=0.0
    )
    handler.begin_quiet_window()
    handler.on_created(_tags_event(tmp_path))
    assert handler._timer is not None
    handler.cancel()


def test_watch_schedules_after_quiet_window(tmp_path: Path) -> None:
    handler, _fires = _handler(
        tmp_path, frozenset(), startup_quiet_sec=0.05
    )
    handler.begin_quiet_window()
    handler.on_created(_tags_event(tmp_path))
    assert handler._timer is None
    time.sleep(0.06)
    handler.on_created(_tags_event(tmp_path))
    assert handler._timer is not None
    handler.cancel()
