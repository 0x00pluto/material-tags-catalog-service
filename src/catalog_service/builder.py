"""扫描合并 material-tags-catalog.jsonl（原子写）。"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Iterator

from src.catalog_service.config import parse_exclude_dir_names
from src.catalog_service.media_guess import guess_media_path
from src.catalog_service.models import (
    CATALOG_FILENAME,
    SUFFIX,
    BuildResult,
    CatalogRecord,
    load_material_tags,
    stem_from_tags_path,
)

logger = logging.getLogger(__name__)


def path_has_excluded_dir_name(
    path: Path | str,
    root: Path | str,
    exclude_names: frozenset[str] | Sequence[str] | None,
) -> bool:
    """相对 root 的任一路径段精确命中排除名则 True。"""
    names = (
        exclude_names
        if isinstance(exclude_names, frozenset)
        else parse_exclude_dir_names(exclude_names)
    )
    if not names:
        return False
    root_path = Path(root).resolve()
    tag_path = Path(path).resolve()
    try:
        rel = tag_path.relative_to(root_path)
    except ValueError:
        rel = tag_path
    return any(part in names for part in rel.parts)


def iter_material_tags(
    root: Path | str,
    *,
    catalog_filename: str = CATALOG_FILENAME,
    exclude_dir_names: frozenset[str] | Sequence[str] | None = None,
) -> Iterator[Path]:
    """递归查找 *.material-tags.json，跳过 catalog 文件名与排除目录。"""
    root_path = Path(root)
    exclude_set = (
        exclude_dir_names
        if isinstance(exclude_dir_names, frozenset)
        else parse_exclude_dir_names(exclude_dir_names)
    )
    for path in sorted(root_path.rglob(f"*{SUFFIX}")):
        if path.name == catalog_filename:
            continue
        if not path.is_file():
            continue
        if path_has_excluded_dir_name(path, root_path, exclude_set):
            continue
        yield path


def catalog_record(tags_path: Path, root: Path) -> CatalogRecord:
    tags = load_material_tags(tags_path)
    stem = stem_from_tags_path(tags_path)
    rel = tags_path.resolve().relative_to(root.resolve()).as_posix()
    media = guess_media_path(tags_path)
    media_rel = (
        media.resolve().relative_to(root.resolve()).as_posix() if media else None
    )
    return CatalogRecord(
        stem=stem,
        tags_path=rel,
        media_guess=media_rel,
        schema_version=tags.get("schema_version"),
        generated_at=tags.get("generated_at"),
        title=str(tags["title"]),
        description=str(tags["description"]),
        keywords=str(tags["keywords"]),
        width=tags.get("width"),
        height=tags.get("height"),
        duration_s=tags.get("duration_s"),
        aspect_ratio=tags.get("aspect_ratio"),
        orientation=tags.get("orientation"),
    )


def build_catalog(
    root: Path | str,
    out: Path | str,
    *,
    trigger: str = "cli",
    exclude_dir_names: frozenset[str] | Sequence[str] | None = None,
    purge_orphan_tags: bool = True,
) -> BuildResult:
    """扫描 root 下标签文件，原子写入 jsonl。

    排除目录内标签不读不写；合法 orphan（无原媒体）默认物理删除标签文件。
    """
    root_path = Path(root)
    out_path = Path(out)
    if not root_path.is_dir():
        raise FileNotFoundError(f"扫描根不存在或不是目录: {root_path}")

    exclude_set = (
        exclude_dir_names
        if isinstance(exclude_dir_names, frozenset)
        else parse_exclude_dir_names(exclude_dir_names)
    )

    started = time.perf_counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    catalog_name = out_path.name

    written = 0
    skipped_no_media = 0
    skipped_invalid = 0
    skipped_excluded = 0
    purged = 0
    errors: list[str] = []

    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            # 先全量枚举再过滤，以便统计 skipped_excluded
            for tags_path in sorted(root_path.rglob(f"*{SUFFIX}")):
                if tags_path.name == catalog_name:
                    continue
                if not tags_path.is_file():
                    continue
                if path_has_excluded_dir_name(tags_path, root_path, exclude_set):
                    skipped_excluded += 1
                    logger.info("skip excluded %s", tags_path)
                    continue
                try:
                    record = catalog_record(tags_path, root_path)
                except Exception as exc:  # noqa: BLE001 — 单条容错
                    skipped_invalid += 1
                    msg = f"skip {tags_path}: {exc}"
                    errors.append(msg)
                    logger.warning(msg)
                    continue
                if record.media_guess is None:
                    skipped_no_media += 1
                    if purge_orphan_tags:
                        try:
                            tags_path.unlink()
                            purged += 1
                            logger.info(
                                "purged orphan %s: no media (guess_media_path miss)",
                                tags_path,
                            )
                        except OSError as exc:
                            msg = f"purge failed {tags_path}: {exc}"
                            errors.append(msg)
                            logger.warning(msg)
                    else:
                        msg = f"skip {tags_path}: no media (guess_media_path miss)"
                        errors.append(msg)
                        logger.warning(msg)
                    continue
                fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                written += 1
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    skipped = skipped_no_media + skipped_invalid
    duration_ms = int((time.perf_counter() - started) * 1000)
    result = BuildResult(
        written=written,
        skipped=skipped,
        duration_ms=duration_ms,
        trigger=trigger,
        out_path=str(out_path),
        errors=errors[:20],
        skipped_no_media=skipped_no_media,
        skipped_invalid=skipped_invalid,
        skipped_excluded=skipped_excluded,
        purged=purged,
    )
    logger.info(
        "build done trigger=%s written=%s skipped=%s "
        "skipped_no_media=%s skipped_invalid=%s skipped_excluded=%s "
        "purged=%s duration_ms=%s out=%s",
        trigger,
        written,
        skipped,
        skipped_no_media,
        skipped_invalid,
        skipped_excluded,
        purged,
        duration_ms,
        out_path,
    )
    return result
