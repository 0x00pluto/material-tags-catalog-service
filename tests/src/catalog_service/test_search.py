"""search.py 纯函数测试。"""

from __future__ import annotations

import json
from pathlib import Path

from src.catalog_service.search import score_record, search_catalog, tokenize_query


def test_tokenize_query() -> None:
    assert tokenize_query("玄关,衣帽架") == ["玄关", "衣帽架"]
    assert tokenize_query("玄关，衣帽架") == ["玄关", "衣帽架"]
    assert tokenize_query("  foo  bar,baz  ") == ["foo", "bar", "baz"]
    assert tokenize_query("") == []
    assert tokenize_query("   ,，  ") == []
    assert tokenize_query("solo") == ["solo"]


def test_score_and_and_weights() -> None:
    # 仅 keywords 命中 → 3
    assert score_record(["门"], "客厅", "描述", "大门,玄关") == 3
    # title → 2
    assert score_record(["客厅"], "客厅一角", "描述", "其他") == 2
    # description → 1
    assert score_record(["一角"], "标题", "客厅一角", "其他") == 1
    # 同 token 多字段叠加：keywords+title = 5
    assert score_record(["玄关"], "玄关实拍", "描述", "玄关,衣帽") == 5
    # AND 失败
    assert score_record(["玄关", "衣帽架"], "玄关", "描述", "玄关") is None
    # casefold
    assert score_record(["Door"], "title", "desc", "front door") == 3


def test_search_catalog_sort_and_paging(tmp_path: Path) -> None:
    rows = [
        {
            "stem": "B",
            "tags_path": "B.material-tags.json",
            "media_guess": None,
            "schema_version": "1",
            "generated_at": None,
            "title": "玄关",
            "description": "普通",
            "keywords": "其他",
        },
        {
            "stem": "A",
            "tags_path": "A.material-tags.json",
            "media_guess": None,
            "schema_version": "1",
            "generated_at": None,
            "title": "其他",
            "description": "普通",
            "keywords": "玄关",
        },
        {
            "stem": "C",
            "tags_path": "C.material-tags.json",
            "media_guess": None,
            "schema_version": "1",
            "generated_at": None,
            "title": "玄关",
            "description": "普通",
            "keywords": "玄关",
        },
        {
            "stem": "Z",
            "tags_path": "Z.material-tags.json",
            "media_guess": None,
            "schema_version": "1",
            "generated_at": None,
            "title": "无关",
            "description": "无关",
            "keywords": "无关",
        },
    ]
    path = tmp_path / "catalog.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    tokens = ["玄关"]
    # C: kw+title=5；A: kw=3；B: title=2；同分按 stem 升序不冲突
    result = search_catalog(path, tokens, limit=10, offset=0)
    assert result.total_matched == 3
    assert [i["stem"] for i in result.items] == ["C", "A", "B"]

    page1 = search_catalog(path, tokens, limit=2, offset=0)
    page2 = search_catalog(path, tokens, limit=2, offset=2)
    assert [i["stem"] for i in page1.items] == ["C", "A"]
    assert [i["stem"] for i in page2.items] == ["B"]
    assert page1.total_matched == page2.total_matched == 3


def test_search_catalog_tie_break_stem(tmp_path: Path) -> None:
    rows = [
        {
            "stem": "m2",
            "tags_path": "m2.material-tags.json",
            "title": "门",
            "description": "d",
            "keywords": "x",
        },
        {
            "stem": "m1",
            "tags_path": "m1.material-tags.json",
            "title": "门",
            "description": "d",
            "keywords": "x",
        },
    ]
    path = tmp_path / "catalog.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    result = search_catalog(path, ["门"], limit=10, offset=0)
    assert [i["stem"] for i in result.items] == ["m1", "m2"]


def test_search_catalog_skips_bad_lines(tmp_path: Path) -> None:
    path = tmp_path / "catalog.jsonl"
    good = {
        "stem": "ok",
        "tags_path": "ok.material-tags.json",
        "title": "玄关衣帽",
        "description": "d",
        "keywords": "k",
    }
    path.write_text(
        "\n".join(
            [
                "not-json",
                json.dumps({"no_stem": True}),
                "[]",
                json.dumps(good, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = search_catalog(path, ["玄关"], limit=10, offset=0)
    assert result.total_matched == 1
    assert result.items[0]["stem"] == "ok"


def test_search_catalog_and_multi_token(tmp_path: Path) -> None:
    rows = [
        {
            "stem": "both",
            "tags_path": "both.material-tags.json",
            "title": "玄关",
            "description": "有衣帽架",
            "keywords": "入户",
        },
        {
            "stem": "one",
            "tags_path": "one.material-tags.json",
            "title": "玄关",
            "description": "无架",
            "keywords": "入户",
        },
    ]
    path = tmp_path / "catalog.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    result = search_catalog(path, ["玄关", "衣帽架"], limit=10, offset=0)
    assert result.total_matched == 1
    assert result.items[0]["stem"] == "both"


def test_search_passes_v2_media_meta(tmp_path: Path) -> None:
    row = {
        "stem": "v2",
        "tags_path": "v2.material-tags.json",
        "media_guess": "v2.mp4",
        "schema_version": "2",
        "generated_at": "2026-07-30T11:05:03+08:00",
        "title": "玄关衣帽",
        "description": "产品特写",
        "keywords": "竖屏",
        "width": 1080,
        "height": 1920,
        "duration_s": 11.01,
        "aspect_ratio": "9:16",
        "orientation": "竖屏",
    }
    path = tmp_path / "catalog.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    result = search_catalog(path, ["玄关"], limit=5, offset=0)
    assert result.total_matched == 1
    item = result.items[0]
    assert item["width"] == 1080
    assert item["height"] == 1920
    assert item["duration_s"] == 11.01
    assert item["aspect_ratio"] == "9:16"
    assert item["orientation"] == "竖屏"


def test_search_legacy_row_media_meta_null(tmp_path: Path) -> None:
    row = {
        "stem": "legacy",
        "tags_path": "legacy.material-tags.json",
        "title": "玄关",
        "description": "d",
        "keywords": "k",
    }
    path = tmp_path / "catalog.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    result = search_catalog(path, ["玄关"], limit=5, offset=0)
    assert result.total_matched == 1
    item = result.items[0]
    assert item["width"] is None
    assert item["height"] is None
    assert item["duration_s"] is None
    assert item["aspect_ratio"] is None
    assert item["orientation"] is None
