"""扫描合并 material-tags-catalog.jsonl（原子写）。"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterator

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


def iter_material_tags(
    root: Path | str,
    *,
    catalog_filename: str = CATALOG_FILENAME,
) -> Iterator[Path]:
    """递归查找 *.material-tags.json，跳过 catalog 文件名。"""
    root_path = Path(root)
    for path in sorted(root_path.rglob(f"*{SUFFIX}")):
        if path.name == catalog_filename:
            continue
        if not path.is_file():
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
) -> BuildResult:
    """扫描 root 下标签文件，原子写入 jsonl。"""
    root_path = Path(root)
    out_path = Path(out)
    if not root_path.is_dir():
        raise FileNotFoundError(f"扫描根不存在或不是目录: {root_path}")

    started = time.perf_counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    catalog_name = out_path.name

    written = 0
    skipped_no_media = 0
    skipped_invalid = 0
    errors: list[str] = []

    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            for tags_path in iter_material_tags(
                root_path, catalog_filename=catalog_name
            ):
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
    )
    logger.info(
        "build done trigger=%s written=%s skipped=%s "
        "skipped_no_media=%s skipped_invalid=%s duration_ms=%s out=%s",
        trigger,
        written,
        skipped,
        skipped_no_media,
        skipped_invalid,
        duration_ms,
        out_path,
    )
    return result
