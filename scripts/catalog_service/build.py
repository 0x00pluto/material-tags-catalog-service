#!/usr/bin/env python3
"""一次性合并 material-tags-catalog.jsonl。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.catalog_service import __version__  # noqa: E402
from src.catalog_service.builder import build_catalog  # noqa: E402
from src.catalog_service.models import CATALOG_FILENAME  # noqa: E402


def main(
    root: Path | None = typer.Option(
        None, "--root", help="素材库根目录", exists=True, file_okay=False
    ),
    out: Path | None = typer.Option(None, "--out", help="输出 JSONL 路径"),
    version: bool = typer.Option(False, "--version", help="打印版本并退出"),
) -> None:
    """Build material-tags-catalog.jsonl once."""
    if version:
        typer.echo(__version__)
        raise SystemExit(0)
    if root is None:
        typer.echo("缺少 --root（或使用 --version）", err=True)
        raise SystemExit(2)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    out_path = out if out is not None else root / CATALOG_FILENAME
    result = build_catalog(root, out_path, trigger="cli")
    print(result.out_path)
    print(
        f"written={result.written} skipped={result.skipped} "
        f"skipped_no_media={result.skipped_no_media} "
        f"skipped_invalid={result.skipped_invalid} "
        f"duration_ms={result.duration_ms}",
        file=sys.stderr,
    )
    raise SystemExit(0 if result.skipped == 0 else 1)


if __name__ == "__main__":
    typer.run(main)
