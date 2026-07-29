"""builder / media_guess 单测。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.catalog_service.builder import build_catalog, catalog_record, iter_material_tags
from src.catalog_service.media_guess import guess_media_path
from src.catalog_service.models import (
    CATALOG_FILENAME,
    SUFFIX,
    load_material_tags,
    stem_from_tags_path,
    tags_filename_for_stem,
    validate_tags,
)

SAMPLE_TAGS = {
    "schema_version": "1",
    "generated_at": "2026-07-29T09:00:00+08:00",
    "title": "测试标题",
    "description": "测试描述内容",
    "keywords": "测试, 关键词",
}


def _write_tags(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_stem_and_validate() -> None:
    assert stem_from_tags_path(f"clip{SUFFIX}") == "clip"
    with pytest.raises(ValueError):
        stem_from_tags_path("x.json")
    with pytest.raises(ValueError):
        validate_tags({"title": "a"})


def test_iter_skips_plain_json(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / CATALOG_FILENAME).write_text("{}\n", encoding="utf-8")
    good = tmp_path / "sub" / tags_filename_for_stem("a")
    _write_tags(good, SAMPLE_TAGS)
    assert list(iter_material_tags(tmp_path)) == [good]


def test_guess_media_and_catalog_record(tmp_path: Path) -> None:
    stem = "clip1"
    tags_path = tmp_path / tags_filename_for_stem(stem)
    _write_tags(tags_path, SAMPLE_TAGS)
    media = tmp_path / f"{stem}.mp4"
    media.write_bytes(b"fake")
    assert guess_media_path(tags_path) == media
    record = catalog_record(tags_path, tmp_path)
    assert record.stem == stem
    assert record.tags_path == tags_path.name
    assert record.media_guess == media.name
    assert record.title == SAMPLE_TAGS["title"]


def test_build_catalog_atomic_and_skip(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    _write_tags(root / tags_filename_for_stem("one"), SAMPLE_TAGS)
    bad = root / tags_filename_for_stem("bad")
    bad.write_text("{not-json", encoding="utf-8")
    (root / "noise.json").write_text('{"a":1}\n', encoding="utf-8")
    (root / "one.mp4").write_bytes(b"x")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 1
    assert result.skipped == 1
    assert result.trigger == "test"
    assert out.is_file()
    assert not out.with_suffix(out.suffix + ".tmp").exists()

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["stem"] == "one"
    assert row["media_guess"] == "one.mp4"
    assert row["schema_version"] == "1"


def test_load_legacy_meta_null(tmp_path: Path) -> None:
    path = tmp_path / tags_filename_for_stem("legacy")
    _write_tags(
        path,
        {
            "title": "t",
            "description": "d",
            "keywords": "k",
        },
    )
    loaded = load_material_tags(path)
    assert loaded["schema_version"] is None
    assert loaded["generated_at"] is None
