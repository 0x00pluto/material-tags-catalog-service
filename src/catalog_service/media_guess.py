"""媒体文件猜测（同目录；`.material_index` 时可查直接父目录）。"""

from __future__ import annotations

from pathlib import Path

from src.catalog_service.models import SUFFIX, stem_from_tags_path

MATERIAL_INDEX_DIR = ".material_index"

MEDIA_EXTENSIONS = (
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".wav",
    ".mp3",
)


def _guess_in_directory(
    directory: Path,
    stem: str,
    *,
    exclude: Path,
) -> Path | None:
    """在 directory 下按白名单扩展名顺序找与 stem 同名的媒体文件。"""
    if not directory.is_dir():
        return None
    by_ext: dict[str, Path] = {}
    exclude_resolved = exclude.resolve()
    for sibling in directory.iterdir():
        if not sibling.is_file() or sibling.resolve() == exclude_resolved:
            continue
        prefix = f"{stem}."
        if not sibling.name.startswith(prefix):
            continue
        if sibling.name.endswith(SUFFIX):
            continue
        ext = sibling.suffix.lower()
        if ext in MEDIA_EXTENSIONS:
            by_ext.setdefault(ext, sibling)
    for ext in MEDIA_EXTENSIONS:
        found = by_ext.get(ext)
        if found is not None:
            return found
    return None


def guess_media_path(tags_path: Path | str) -> Path | None:
    """猜测原媒体路径。

    1. 先在标签同目录按白名单与 stem 查找；
    2. 未命中且父目录名为 `.material_index` 时，再查直接父目录；
    3. 其它情况不上翻。
    """
    path = Path(tags_path)
    stem = stem_from_tags_path(path)
    parent = path.parent
    found = _guess_in_directory(parent, stem, exclude=path)
    if found is not None:
        return found
    if parent.name == MATERIAL_INDEX_DIR:
        return _guess_in_directory(parent.parent, stem, exclude=path)
    return None
