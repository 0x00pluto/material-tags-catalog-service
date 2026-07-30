"""watcher 排除路径降噪单测。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.catalog_service.models import tags_filename_for_stem
from src.catalog_service.watcher import _DebouncedTagsHandler


def _handler(tmp_path: Path, exclude: frozenset[str]) -> tuple[_DebouncedTagsHandler, list[int]]:
    fires: list[int] = []

    def on_change() -> None:
        fires.append(1)

    handler = _DebouncedTagsHandler(
        0.01,
        on_change,
        root=tmp_path,
        exclude_dir_names=exclude,
    )
    return handler, fires


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
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(tmp_path / "ok" / tags_filename_for_stem("x"))

    handler.on_created(event)
    assert handler._timer is not None
    handler.cancel()
