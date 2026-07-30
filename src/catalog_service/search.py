"""Catalog 关键词检索：分词、AND 子串、字段加权排序。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# keywords +3 / title +2 / description +1；同一 token 每字段最多计一次
_WEIGHT_KEYWORDS = 3
_WEIGHT_TITLE = 2
_WEIGHT_DESCRIPTION = 1

_TOKEN_SPLIT = re.compile(r"[\s,，]+")


@dataclass(frozen=True)
class SearchResult:
    total_matched: int
    items: list[dict[str, Any]]


def tokenize_query(q: str) -> list[str]:
    """按空白与中英文逗号拆分；去空 token。"""
    if not q:
        return []
    return [t for t in _TOKEN_SPLIT.split(q.strip()) if t]


def score_record(
    tokens: list[str],
    title: str,
    description: str,
    keywords: str,
) -> int | None:
    """AND 子串匹配并加权打分；未全命中返回 None。

    匹配对 haystack / needle 做 casefold。同一 token 在某字段命中至多加一次该字段权重。
    """
    if not tokens:
        return None

    title_cf = title.casefold()
    desc_cf = description.casefold()
    kw_cf = keywords.casefold()

    total = 0
    for token in tokens:
        needle = token.casefold()
        hit = False
        if needle in kw_cf:
            total += _WEIGHT_KEYWORDS
            hit = True
        if needle in title_cf:
            total += _WEIGHT_TITLE
            hit = True
        if needle in desc_cf:
            total += _WEIGHT_DESCRIPTION
            hit = True
        if not hit:
            return None
    return total


def _row_from_obj(obj: dict[str, Any]) -> dict[str, Any] | None:
    """从解析后的对象抽出 catalog 行；缺关键字段则视为坏行。"""
    stem = obj.get("stem")
    if stem is None or str(stem).strip() == "":
        return None
    return {
        "stem": str(stem),
        "tags_path": str(obj.get("tags_path") or ""),
        "media_guess": obj.get("media_guess"),
        "schema_version": obj.get("schema_version"),
        "generated_at": obj.get("generated_at"),
        "title": str(obj.get("title") or ""),
        "description": str(obj.get("description") or ""),
        "keywords": str(obj.get("keywords") or ""),
        "width": obj.get("width"),
        "height": obj.get("height"),
        "duration_s": obj.get("duration_s"),
        "aspect_ratio": obj.get("aspect_ratio"),
        "orientation": obj.get("orientation"),
    }


def search_catalog(
    path: Path | str,
    tokens: list[str],
    *,
    limit: int = 20,
    offset: int = 0,
) -> SearchResult:
    """扫描 JSONL：AND 匹配 → 加权排序 → offset/limit 切片。坏行跳过。"""
    if not tokens:
        return SearchResult(total_matched=0, items=[])
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    scored: list[tuple[int, str, dict[str, Any]]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            row = _row_from_obj(obj)
            if row is None:
                continue
            score = score_record(
                tokens,
                row["title"],
                row["description"],
                row["keywords"],
            )
            if score is None:
                continue
            scored.append((score, row["stem"], row))

    scored.sort(key=lambda t: (-t[0], t[1]))
    total = len(scored)
    page = [row for _, _, row in scored[offset : offset + limit]]
    return SearchResult(total_matched=total, items=page)
