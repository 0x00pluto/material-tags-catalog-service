"""同目录媒体文件猜测。"""

from __future__ import annotations

from pathlib import Path

from src.catalog_service.models import SUFFIX, stem_from_tags_path

MEDIA_EXTENSIONS = (
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".jpg",
    ".jpeg",
    ".png",
    ".wav",
    ".mp3",
)


def guess_media_path(tags_path: Path | str) -> Path | None:
    """同目录下寻找与 stem 同名的媒体文件；按白名单扩展名顺序取第一个存在的。"""
    path = Path(tags_path)
    stem = stem_from_tags_path(path)
    by_ext: dict[str, Path] = {}
    for sibling in path.parent.iterdir():
        if not sibling.is_file() or sibling.resolve() == path.resolve():
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
