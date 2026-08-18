"""search.py 纯函数测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.catalog_service.search import (
    PATH_PREFIX_MAX,
    PathPrefixError,
    normalize_path_prefixes,
    score_record,
    search_catalog,
    tags_path_matches_any_prefix,
    tokenize_query,
)


def test_tokenize_query() -> None:
    assert tokenize_query("玄关,衣帽架") == ["玄关", "衣帽架"]
    assert tokenize_query("玄关，衣帽架") == ["玄关", "衣帽架"]
    assert tokenize_query("  foo  bar,baz  ") == ["foo", "bar", "baz"]
    assert tokenize_query("") == []
    assert tokenize_query("   ,，  ") == []
    assert tokenize_query("solo") == ["solo"]


def test_normalize_path_prefixes_basic() -> None:
    assert normalize_path_prefixes(None) == []
    assert normalize_path_prefixes([]) == []
    assert normalize_path_prefixes(["", "  "]) == []
    assert normalize_path_prefixes([r"蜜梨的素材库\子目录"]) == ["蜜梨的素材库/子目录"]
    # 去首尾 /、保序去重
    assert normalize_path_prefixes(["项目A/", "项目B", "项目A", "项目B/"]) == [
        "项目A",
        "项目B",
    ]


def test_normalize_path_prefixes_rejects_absolute_and_dotdot() -> None:
    with pytest.raises(PathPrefixError):
        normalize_path_prefixes(["/绝对路径"])
    with pytest.raises(PathPrefixError):
        normalize_path_prefixes([r"\绝对"])  # 变为 /绝对
    with pytest.raises(PathPrefixError):
        normalize_path_prefixes([".."])
    with pytest.raises(PathPrefixError):
        normalize_path_prefixes(["foo/../bar"])
    with pytest.raises(PathPrefixError):
        normalize_path_prefixes(["a/../../b"])


def test_normalize_path_prefixes_max() -> None:
    ok = [f"p{i}" for i in range(PATH_PREFIX_MAX)]
    assert len(normalize_path_prefixes(ok)) == PATH_PREFIX_MAX
    with pytest.raises(PathPrefixError):
        normalize_path_prefixes([f"p{i}" for i in range(PATH_PREFIX_MAX + 1)])


def test_tags_path_matches_directory_boundary() -> None:
    assert tags_path_matches_any_prefix("项目A", ["项目A"])
    assert tags_path_matches_any_prefix("项目A/x.material-tags.json", ["项目A"])
    assert not tags_path_matches_any_prefix(
        "项目A备份/x.material-tags.json", ["项目A"]
    )
    assert tags_path_matches_any_prefix("任意", [])
    # OR
    assert tags_path_matches_any_prefix("B/y.json", ["A", "B"])
    assert not tags_path_matches_any_prefix("C/y.json", ["A", "B"])


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
    # 仅 subtitle → 1；低于仅 keywords（3）
    assert score_record(["武汉"], "标题", "描述", "其他", "跑遍了整个武汉") == 1
    assert (
        score_record(["武汉"], "标题", "描述", "其他", "跑遍了整个武汉")
        < score_record(["门"], "客厅", "描述", "大门,玄关")
    )
    # 同 token 落在 description + subtitle 可叠加
    assert score_record(["武汉"], "标题", "去了武汉", "其他", "跑遍了整个武汉") == 2
    # subtitle casefold
    assert score_record(["WUHAN"], "t", "d", "k", "visited Wuhan") == 1


def _write_catalog(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


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
    _write_catalog(path, rows)

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


def test_search_catalog_path_prefix_filter(tmp_path: Path) -> None:
    rows = [
        {
            "stem": "in_a",
            "tags_path": "项目A/in_a.material-tags.json",
            "title": "图",
            "description": "d",
            "keywords": "k",
        },
        {
            "stem": "sibling",
            "tags_path": "项目A备份/sibling.material-tags.json",
            "title": "图",
            "description": "d",
            "keywords": "k",
        },
        {
            "stem": "in_b",
            "tags_path": "项目B/in_b.material-tags.json",
            "title": "图",
            "description": "d",
            "keywords": "k",
        },
        {
            "stem": "exact_dir",
            "tags_path": "项目A",
            "title": "图",
            "description": "d",
            "keywords": "k",
        },
    ]
    path = tmp_path / "catalog.jsonl"
    _write_catalog(path, rows)

    # 未传前缀：全库
    all_hit = search_catalog(path, ["图"], limit=20, offset=0)
    assert all_hit.total_matched == 4

    only_a = search_catalog(
        path, ["图"], limit=20, offset=0, path_prefixes=["项目A"]
    )
    assert only_a.total_matched == 2
    assert {i["stem"] for i in only_a.items} == {"in_a", "exact_dir"}

    # 多前缀 OR
    a_or_b = search_catalog(
        path, ["图"], limit=20, offset=0, path_prefixes=["项目A", "项目B"]
    )
    assert a_or_b.total_matched == 3
    assert {i["stem"] for i in a_or_b.items} == {"in_a", "exact_dir", "in_b"}


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
    _write_catalog(path, rows)
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
    _write_catalog(path, rows)
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
    assert "subtitle" not in item


def test_search_subtitle_only_hit(tmp_path: Path) -> None:
    rows = [
        {
            "stem": "talk",
            "tags_path": "talk.material-tags.json",
            "title": "访谈成片",
            "description": "受访者谈城市见闻",
            "keywords": "访谈, 成片",
            "subtitle": "我跑遍了整个武汉，把街头巷尾都走了一遍",
        },
        {
            "stem": "other",
            "tags_path": "other.material-tags.json",
            "title": "风景",
            "description": "城市空镜",
            "keywords": "空镜",
            "subtitle": "",
        },
    ]
    path = tmp_path / "catalog.jsonl"
    _write_catalog(path, rows)
    result = search_catalog(path, ["跑遍了整个武汉"], limit=10, offset=0)
    assert result.total_matched == 1
    assert result.items[0]["stem"] == "talk"
    assert "subtitle" not in result.items[0]


def test_search_and_title_plus_subtitle(tmp_path: Path) -> None:
    rows = [
        {
            "stem": "both",
            "tags_path": "both.material-tags.json",
            "title": "访谈成片",
            "description": "要点",
            "keywords": "口播",
            "subtitle": "跑遍了整个武汉",
        },
        {
            "stem": "title_only",
            "tags_path": "title_only.material-tags.json",
            "title": "访谈成片",
            "description": "要点",
            "keywords": "口播",
            "subtitle": "",
        },
        {
            "stem": "sub_only",
            "tags_path": "sub_only.material-tags.json",
            "title": "别的标题",
            "description": "要点",
            "keywords": "口播",
            "subtitle": "跑遍了整个武汉",
        },
    ]
    path = tmp_path / "catalog.jsonl"
    _write_catalog(path, rows)
    result = search_catalog(path, ["访谈成片", "跑遍了整个武汉"], limit=10, offset=0)
    assert result.total_matched == 1
    assert result.items[0]["stem"] == "both"


def test_search_legacy_row_missing_subtitle_key(tmp_path: Path) -> None:
    row = {
        "stem": "legacy",
        "tags_path": "legacy.material-tags.json",
        "title": "访谈",
        "description": "要点",
        "keywords": "口播",
    }
    path = tmp_path / "catalog.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    miss = search_catalog(path, ["跑遍了整个武汉"], limit=5, offset=0)
    assert miss.total_matched == 0
    hit = search_catalog(path, ["访谈"], limit=5, offset=0)
    assert hit.total_matched == 1
    assert "subtitle" not in hit.items[0]
