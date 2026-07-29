#!/usr/bin/env python3
"""PyInstaller 入口：常驻 serve。"""

from __future__ import annotations

import os
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
from pydantic import ValidationError  # noqa: E402

from src.catalog_service import __version__  # noqa: E402
from src.catalog_service.config import Settings  # noqa: E402
from src.catalog_service.service import run_serve  # noqa: E402

app = typer.Typer(add_completion=False, help="Serve catalog index")


@app.callback(invoke_without_command=True)
def main(
    root: Path | None = typer.Option(None, "--root"),
    out: Path | None = typer.Option(None, "--out"),
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port"),
    watch: bool | None = typer.Option(None, "--watch/--no-watch"),
    schedule: bool | None = typer.Option(None, "--schedule/--no-schedule"),
    version: bool = typer.Option(False, "--version", help="打印版本并退出"),
) -> None:
    if version:
        typer.echo(__version__)
        raise SystemExit(0)
    if root is not None:
        os.environ["CATALOG_ROOT"] = str(root)
    try:
        settings = Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        typer.echo("缺少 CATALOG_ROOT。请配置同目录 .env 或传入 --root。", err=True)
        typer.echo(str(exc), err=True)
        raise SystemExit(2) from exc
    if out is not None:
        settings.catalog_out = out
    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port
    if watch is not None:
        settings.watch_enabled = watch
    if schedule is not None:
        settings.schedule_enabled = schedule
    run_serve(settings)


if __name__ == "__main__":
    app()
