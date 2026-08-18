"""Catalog 关键词检索：分词、AND 子串、字段加权排序、可选路径前缀过滤。"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# keywords +3 / title +2 / description +1 / subtitle +1；同一 token 每字段最多计一次
_WEIGHT_KEYWORDS = 3
_WEIGHT_TITLE = 2
_WEIGHT_DESCRIPTION = 1
_WEIGHT_SUBTITLE = 1

_TOKEN_SPLIT = re.compile(r"[\s,，]+")

PATH_PREFIX_MAX = 20


class PathPrefixError(ValueError):
    """path_prefix 非法或超过上限。"""


@dataclass(frozen=True)
class SearchResult:
    total_matched: int
    items: list[dict[str, Any]]


def tokenize_query(q: str) -> list[str]:
    """按空白与中英文逗号拆分；去空 token。"""
    if not q:
        return []
    return [t for t in _TOKEN_SPLIT.split(q.strip()) if t]


def normalize_path_prefixes(raw: Sequence[str] | None) -> list[str]:
    """规范化 path_prefix 列表：正斜杠、去首尾 /、空串丢弃、保序去重。

    含 ``..`` 或以 ``/`` 开头（绝对路径语义）→ PathPrefixError。
    规范化后超过 PATH_PREFIX_MAX → PathPrefixError。
    """
    if not raw:
        return []

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if item is None:
            continue
        text = str(item).replace("\\", "/").strip()
        if not text:
            continue
        # 拒绝绝对路径语义（以 / 开头）；勿先 strip 掉首 / 再当相对路径
        if text.startswith("/"):
            raise PathPrefixError("path_prefix must be relative (no leading /)")
        stripped = text.strip("/")
        if not stripped:
            continue
        parts = stripped.split("/")
        if any(p == ".." for p in parts):
            raise PathPrefixError("path_prefix must not contain '..'")
        if stripped in seen:
            continue
        seen.add(stripped)
        out.append(stripped)

    if len(out) > PATH_PREFIX_MAX:
        raise PathPrefixError(
            f"path_prefix count must be <= {PATH_PREFIX_MAX} after normalize"
        )
    return out


def tags_path_matches_any_prefix(
    tags_path: str,
    prefixes: Sequence[str],
) -> bool:
    """目录边界前缀：等于 prefix，或以 ``prefix/`` 开头；空 prefixes 视为通过。"""
    if not prefixes:
        return True
    for prefix in prefixes:
        if tags_path == prefix or tags_path.startswith(prefix + "/"):
            return True
    return False


def _subtitle_from_obj(obj: dict[str, Any]) -> str:
    """历史行无键 / 非 string 当空串；不写入 search items。"""
    raw = obj.get("subtitle")
    return raw if isinstance(raw, str) else ""


def score_record(
    tokens: list[str],
    title: str,
    description: str,
    keywords: str,
    subtitle: str = "",
) -> int | None:
    """AND 子串匹配并加权打分；未全命中返回 None。

    匹配对 haystack / needle 做 casefold。同一 token 在某字段命中至多加一次该字段权重。
    """
    if not tokens:
        return None

    title_cf = title.casefold()
    desc_cf = description.casefold()
    kw_cf = keywords.casefold()
    sub_cf = subtitle.casefold()

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
        if needle in sub_cf:
            total += _WEIGHT_SUBTITLE
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
    path_prefixes: Sequence[str] | None = None,
) -> SearchResult:
    """扫描 JSONL：路径关 → AND 匹配 → 加权排序 → offset/limit 切片。坏行跳过。

    path_prefixes 应为已规范化列表（空 = 全库）；路径关在关键词打分之前。
    """
    if not tokens:
        return SearchResult(total_matched=0, items=[])
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0
    prefixes = list(path_prefixes) if path_prefixes else []

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
            if not tags_path_matches_any_prefix(row["tags_path"], prefixes):
                continue
            score = score_record(
                tokens,
                row["title"],
                row["description"],
                row["keywords"],
                _subtitle_from_obj(obj),
            )
            if score is None:
                continue
            scored.append((score, row["stem"], row))

    scored.sort(key=lambda t: (-t[0], t[1]))
    total = len(scored)
    page = [row for _, _, row in scored[offset : offset + limit]]
    return SearchResult(total_matched=total, items=page)
