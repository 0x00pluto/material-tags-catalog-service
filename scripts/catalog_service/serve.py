#!/usr/bin/env python3
"""常驻：watch + schedule + FastAPI。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.catalog_service import __version__  # noqa: E402
from src.catalog_service.config import Settings  # noqa: E402
from src.catalog_service.service import run_serve  # noqa: E402

cli = typer.Typer(add_completion=False, help="Serve catalog index HTTP + watch + timer")


def _load_settings(
    *,
    root: Path | None,
    out: Path | None,
    host: str | None,
    port: int | None,
    watch: bool | None,
    schedule: bool | None,
) -> Settings:
    if root is not None:
        os.environ["CATALOG_ROOT"] = str(root)
    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception as exc:
        typer.echo(
            "缺少 CATALOG_ROOT。请在 .env 中配置，或传入 --root。",
            err=True,
        )
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
    return settings


@cli.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    root: Path | None = typer.Option(None, "--root", help="覆盖 CATALOG_ROOT"),
    out: Path | None = typer.Option(None, "--out", help="覆盖 CATALOG_OUT"),
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port"),
    watch: bool | None = typer.Option(None, "--watch/--no-watch"),
    schedule: bool | None = typer.Option(None, "--schedule/--no-schedule"),
    version: bool = typer.Option(False, "--version", help="打印版本并退出"),
) -> None:
    if version:
        typer.echo(__version__)
        raise SystemExit(0)
    if ctx.invoked_subcommand is not None:
        return
    settings = _load_settings(
        root=root,
        out=out,
        host=host,
        port=port,
        watch=watch,
        schedule=schedule,
    )
    run_serve(settings)


@cli.command("status")
def status_cmd(
    root: Path | None = typer.Option(None, "--root", help="覆盖 CATALOG_ROOT"),
) -> None:
    """打印当前配置下的 out 路径与是否存在。"""
    settings = _load_settings(
        root=root,
        out=None,
        host=None,
        port=None,
        watch=None,
        schedule=None,
    )
    out_path = settings.resolved_out()
    typer.echo(f"root={settings.catalog_root}")
    typer.echo(f"out={out_path}")
    typer.echo(f"exists={out_path.is_file()}")
    typer.echo(f"version={__version__}")


if __name__ == "__main__":
    cli()
