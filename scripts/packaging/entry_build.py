#!/usr/bin/env python3
"""PyInstaller 入口：一次性 build。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _bootstrap_path() -> None:
    if getattr(sys, "frozen", False):
        return
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_bootstrap_path()

import typer  # noqa: E402

from src.catalog_service import __version__  # noqa: E402
from src.catalog_service.builder import build_catalog  # noqa: E402
from src.catalog_service.models import CATALOG_FILENAME  # noqa: E402


def main(
    root: Path | None = typer.Option(None, "--root", exists=True, file_okay=False),
    out: Path | None = typer.Option(None, "--out"),
    version: bool = typer.Option(False, "--version", help="打印版本并退出"),
) -> None:
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
        f"written={result.written} skipped={result.skipped} duration_ms={result.duration_ms}",
        file=sys.stderr,
    )
    raise SystemExit(0 if result.skipped == 0 else 1)


if __name__ == "__main__":
    typer.run(main)
