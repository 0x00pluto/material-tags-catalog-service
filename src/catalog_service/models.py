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


def load_material_tags(path: Path | str) -> dict[str, str | None]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("material-tags 根节点必须是对象")
    content = validate_tags(data)
    meta = _optional_meta(data)
    return {**content, **meta}


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
