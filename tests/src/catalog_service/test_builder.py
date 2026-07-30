"""builder / media_guess 单测。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.catalog_service.builder import build_catalog, catalog_record, iter_material_tags
from src.catalog_service.media_guess import MATERIAL_INDEX_DIR, guess_media_path
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


def test_guess_media_in_material_index_parent(tmp_path: Path) -> None:
    tagged = tmp_path / "tagged"
    index_dir = tagged / MATERIAL_INDEX_DIR
    stem = "S"
    tags_path = index_dir / tags_filename_for_stem(stem)
    _write_tags(tags_path, SAMPLE_TAGS)
    media = tagged / f"{stem}.mp4"
    media.write_bytes(b"fake")

    assert guess_media_path(tags_path) == media

    out = tmp_path / CATALOG_FILENAME
    result = build_catalog(tmp_path, out, trigger="test")
    assert result.written == 1
    assert result.skipped_no_media == 0
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["stem"] == stem
    assert MATERIAL_INDEX_DIR in row["tags_path"]
    assert row["media_guess"] == "tagged/S.mp4"
    assert (tmp_path / row["media_guess"]).is_file()


def test_guess_media_sibling_preferred_over_parent(tmp_path: Path) -> None:
    tagged = tmp_path / "tagged"
    index_dir = tagged / MATERIAL_INDEX_DIR
    stem = "both"
    tags_path = index_dir / tags_filename_for_stem(stem)
    _write_tags(tags_path, SAMPLE_TAGS)
    sibling = index_dir / f"{stem}.mp4"
    sibling.write_bytes(b"sibling")
    parent_media = tagged / f"{stem}.mp4"
    parent_media.write_bytes(b"parent")

    assert guess_media_path(tags_path) == sibling


def test_build_skips_material_index_without_parent_media(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    index_dir = root / MATERIAL_INDEX_DIR
    _write_tags(index_dir / tags_filename_for_stem("lonely"), SAMPLE_TAGS)
    # 父目录无白名单媒体；非白名单扩展名不算
    (root / "lonely.avi").write_bytes(b"x")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 0
    assert result.skipped_no_media >= 1
    assert "lonely" not in out.read_text(encoding="utf-8")


def test_build_mixed_layouts_in_one_root(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()

    # 旧：同目录布局
    _write_tags(root / "old" / tags_filename_for_stem("oldclip"), SAMPLE_TAGS)
    (root / "old" / "oldclip.mp4").write_bytes(b"x")

    # 新：.material_index 父目录布局
    tagged = root / "new"
    _write_tags(
        tagged / MATERIAL_INDEX_DIR / tags_filename_for_stem("newclip"),
        SAMPLE_TAGS,
    )
    (tagged / "newclip.mp4").write_bytes(b"y")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 2
    assert result.skipped_no_media == 0
    rows = {
        json.loads(line)["stem"]: json.loads(line)
        for line in out.read_text(encoding="utf-8").strip().splitlines()
    }
    assert rows["oldclip"]["media_guess"] == "old/oldclip.mp4"
    assert rows["newclip"]["media_guess"] == "new/newclip.mp4"
    assert MATERIAL_INDEX_DIR in rows["newclip"]["tags_path"]


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
    assert result.skipped_invalid == 1
    assert result.skipped_no_media == 0
    assert result.trigger == "test"
    assert out.is_file()
    assert not out.with_suffix(out.suffix + ".tmp").exists()

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["stem"] == "one"
    assert row["media_guess"] == "one.mp4"
    assert row["schema_version"] == "1"


def test_build_skips_orphan_tags_without_media(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    _write_tags(root / tags_filename_for_stem("orphan"), SAMPLE_TAGS)
    # 白名单外扩展名视为无原媒体
    (root / "orphan.avi").write_bytes(b"x")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 0
    assert result.skipped == 1
    assert result.skipped_no_media == 1
    assert result.skipped_invalid == 0
    assert out.is_file()
    assert out.read_text(encoding="utf-8").strip() == ""
    assert any("no media" in e for e in result.errors)


def test_build_writes_when_media_present(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    _write_tags(root / tags_filename_for_stem("clip"), SAMPLE_TAGS)
    (root / "clip.mp4").write_bytes(b"x")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 1
    assert result.skipped == 0
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["stem"] == "clip"
    assert row["media_guess"] == "clip.mp4"


def test_build_removes_row_after_media_deleted(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    _write_tags(root / tags_filename_for_stem("gone"), SAMPLE_TAGS)
    media = root / "gone.mp4"
    media.write_bytes(b"x")
    out = root / CATALOG_FILENAME

    first = build_catalog(root, out, trigger="test")
    assert first.written == 1
    assert "gone" in out.read_text(encoding="utf-8")

    media.unlink()
    second = build_catalog(root, out, trigger="test")
    assert second.written == 0
    assert second.skipped_no_media == 1
    assert "gone" not in out.read_text(encoding="utf-8")


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
    assert loaded["width"] is None
    assert loaded["height"] is None
    assert loaded["duration_s"] is None
    assert loaded["aspect_ratio"] is None
    assert loaded["orientation"] is None


SAMPLE_TAGS_V2 = {
    "schema_version": "2",
    "generated_at": "2026-07-30T11:05:03+08:00",
    "title": "逛园区_玄关衣帽鞋凳特写",
    "description": "竖屏9:16无人物产品特写",
    "keywords": "玄关衣帽架, 鞋凳, 竖屏",
    "width": 1080,
    "height": 1920,
    "duration_s": 11.01,
    "aspect_ratio": "9:16",
    "orientation": "竖屏",
}


def test_build_catalog_v2_media_meta(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    _write_tags(root / tags_filename_for_stem("v2clip"), SAMPLE_TAGS_V2)
    (root / "v2clip.mp4").write_bytes(b"x")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 1
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["schema_version"] == "2"
    assert row["width"] == 1080
    assert row["height"] == 1920
    assert row["duration_s"] == 11.01
    assert row["aspect_ratio"] == "9:16"
    assert row["orientation"] == "竖屏"


def test_build_catalog_v1_media_meta_null(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    _write_tags(root / tags_filename_for_stem("v1clip"), SAMPLE_TAGS)
    (root / "v1clip.mp4").write_bytes(b"x")

    out = root / CATALOG_FILENAME
    result = build_catalog(root, out, trigger="test")
    assert result.written == 1
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["width"] is None
    assert row["height"] is None
    assert row["duration_s"] is None
    assert row["aspect_ratio"] is None
    assert row["orientation"] is None


def test_load_bad_media_meta_becomes_null(tmp_path: Path) -> None:
    path = tmp_path / tags_filename_for_stem("badmeta")
    _write_tags(
        path,
        {
            "title": "t",
            "description": "d",
            "keywords": "k",
            "width": "not-a-number",
            "height": True,
            "duration_s": {},
            "aspect_ratio": "  ",
            "orientation": None,
        },
    )
    loaded = load_material_tags(path)
    assert loaded["width"] is None
    assert loaded["height"] is None
    assert loaded["duration_s"] is None
    assert loaded["aspect_ratio"] is None
    assert loaded["orientation"] is None
