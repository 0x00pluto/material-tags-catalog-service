"""标签文件校验与 catalog 行模型。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

SUFFIX = ".material-tags.json"
CATALOG_FILENAME = "material-tags-catalog.jsonl"

_REQUIRED_KEYS = ("title", "description", "keywords")
_META_KEYS = ("schema_version", "generated_at")
# schema v2 可选媒体元数据；缺省 / 坏类型 → null，不拖垮入库
_MEDIA_META_INT_KEYS = ("width", "height")
_MEDIA_META_FLOAT_KEYS = ("duration_s",)
_MEDIA_META_STR_KEYS = ("aspect_ratio", "orientation")


def tags_filename_for_stem(stem: str) -> str:
    return f"{stem}{SUFFIX}"


def stem_from_tags_path(path: Path | str) -> str:
    """从 `<stem>.material-tags.json` 解析 stem；后缀不符则报错。"""
    name = Path(path).name
    if not name.endswith(SUFFIX):
        raise ValueError(f"不是 {SUFFIX} 文件: {name}")
    stem = name[: -len(SUFFIX)]
    if not stem:
        raise ValueError(f"无法从文件名解析 stem: {name}")
    return stem


def split_keywords(keywords: str | Sequence[str]) -> list[str]:
    if isinstance(keywords, str):
        parts = re.split(r"[,，]", keywords)
    else:
        parts = list(keywords)
    return [str(p).strip() for p in parts if p and str(p).strip()]


def validate_tags(tags: Mapping[str, object]) -> dict[str, str]:
    """校验并规范化内容三字段。"""
    missing = [k for k in _REQUIRED_KEYS if k not in tags or tags[k] is None]
    if missing:
        raise ValueError(f"tags 缺少字段: {', '.join(missing)}")
    title = str(tags["title"]).strip()
    description = str(tags["description"]).strip()
    keywords_raw = tags["keywords"]
    if not title:
        raise ValueError("title 不能为空")
    if not description:
        raise ValueError("description 不能为空")
    if isinstance(keywords_raw, str):
        keywords = keywords_raw.strip()
    else:
        keywords = ", ".join(split_keywords(keywords_raw))  # type: ignore[arg-type]
    if not keywords:
        raise ValueError("keywords 不能为空")
    return {
        "title": title,
        "description": description,
        "keywords": keywords,
    }


def _optional_meta(data: Mapping[str, object]) -> dict[str, str | None]:
    meta: dict[str, str | None] = {}
    for key in _META_KEYS:
        raw = data.get(key)
        if raw is None:
            meta[key] = None
        else:
            text = str(raw).strip()
            meta[key] = text or None
    return meta


def _optional_int(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return None
        return int(raw)
    try:
        text = str(raw).strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _optional_float(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value != value:  # NaN
            return None
        return value
    try:
        text = str(raw).strip()
        if not text:
            return None
        value = float(text)
        if value != value:
            return None
        return value
    except (TypeError, ValueError):
        return None


def _optional_str(raw: object) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _optional_media_meta(
    data: Mapping[str, object],
) -> dict[str, int | float | str | None]:
    meta: dict[str, int | float | str | None] = {}
    for key in _MEDIA_META_INT_KEYS:
        meta[key] = _optional_int(data.get(key))
    for key in _MEDIA_META_FLOAT_KEYS:
        meta[key] = _optional_float(data.get(key))
    for key in _MEDIA_META_STR_KEYS:
        meta[key] = _optional_str(data.get(key))
    return meta


def load_material_tags(path: Path | str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("material-tags 根节点必须是对象")
    content = validate_tags(data)
    meta = _optional_meta(data)
    media_meta = _optional_media_meta(data)
    return {**content, **meta, **media_meta}


@dataclass
class CatalogRecord:
    stem: str
    tags_path: str
    media_guess: str | None
    schema_version: str | None
    generated_at: str | None
    title: str
    description: str
    keywords: str
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    aspect_ratio: str | None = None
    orientation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BuildResult:
    written: int
    skipped: int
    duration_ms: int
    trigger: str
    out_path: str
    errors: list[str] = field(default_factory=list)
    # 原因拆分；skipped == skipped_no_media + skipped_invalid（不含 excluded）
    skipped_no_media: int = 0
    skipped_invalid: int = 0
    # 扫描排除命中（未读文件）；与 skipped 并列
    skipped_excluded: int = 0
    # 合法 orphan 物理删除成功条数（仍计入 skipped_no_media）
    purged: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
