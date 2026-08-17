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
    ".gif",
    ".wav",
    ".mp3",
)

# 单次 build 内复用同一目录的 iterdir 结果；键为 resolve() 后的目录
DirListingCache = dict[Path, list[Path]]


def _list_directory_entries(
    directory: Path,
    *,
    dir_listing_cache: DirListingCache | None,
) -> list[Path]:
    """列出 directory 下条目；有 cache 时按 resolve 键复用。"""
    if dir_listing_cache is None:
        return list(directory.iterdir())
    key = directory.resolve()
    cached = dir_listing_cache.get(key)
    if cached is not None:
        return cached
    entries = list(directory.iterdir())
    dir_listing_cache[key] = entries
    return entries


def _guess_in_directory(
    directory: Path,
    stem: str,
    *,
    exclude: Path,
    dir_listing_cache: DirListingCache | None = None,
) -> Path | None:
    """在 directory 下按白名单扩展名顺序找与 stem 同名的媒体文件。"""
    if not directory.is_dir():
        return None
    by_ext: dict[str, Path] = {}
    exclude_resolved = exclude.resolve()
    for sibling in _list_directory_entries(
        directory, dir_listing_cache=dir_listing_cache
    ):
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


def guess_media_path(
    tags_path: Path | str,
    *,
    dir_listing_cache: DirListingCache | None = None,
) -> Path | None:
    """猜测原媒体路径。

    1. 先在标签同目录按白名单与 stem 查找；
    2. 未命中且父目录名为 `.material_index` 时，再查直接父目录；
    3. 其它情况不上翻。

    ``dir_listing_cache`` 仅供单次 ``build_catalog`` 复用目录 listing；
    默认 None，无缓存调用行为与改前一致。
    """
    path = Path(tags_path)
    stem = stem_from_tags_path(path)
    parent = path.parent
    found = _guess_in_directory(
        parent, stem, exclude=path, dir_listing_cache=dir_listing_cache
    )
    if found is not None:
        return found
    if parent.name == MATERIAL_INDEX_DIR:
        return _guess_in_directory(
            parent.parent,
            stem,
            exclude=path,
            dir_listing_cache=dir_listing_cache,
        )
    return None
