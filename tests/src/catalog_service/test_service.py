"""run_serve 非阻塞 startup 单测。"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from src.catalog_service.build_lock import BuildLock
from src.catalog_service.config import Settings
from src.catalog_service.models import BuildResult
from src.catalog_service.service import run_serve


def test_run_serve_does_not_join_startup_before_uvicorn(
    tmp_path: Path, monkeypatch
) -> None:
    """主路径在 startup build 完成前就进入 uvicorn.run（不 join 后台线程）。"""
    root = tmp_path / "media"
    root.mkdir()
    settings = Settings(
        CATALOG_ROOT=root,
        HOST="127.0.0.1",
        PORT=18787,
        WATCH_ENABLED=False,
        SCHEDULE_ENABLED=False,
    )

    startup_entered = threading.Event()
    release_startup = threading.Event()
    uvicorn_called = threading.Event()
    request_calls: list[str] = []

    def fake_request(self, trigger: str, runner):
        request_calls.append(trigger)
        if trigger == "startup":
            startup_entered.set()
            assert release_startup.wait(timeout=5)
            return (
                BuildResult(
                    written=0,
                    skipped=0,
                    duration_ms=1,
                    trigger="startup",
                    out_path=str(settings.resolved_out()),
                    errors=[],
                ),
                False,
            )
        return None, False

    def fake_uvicorn_run(app, **_kwargs):
        uvicorn_called.set()

        async def _drive() -> None:
            async with app.router.lifespan_context(app):
                assert startup_entered.wait(timeout=5)
                # startup 仍被挡住 → 证明 uvicorn/lifespan 未 join 该线程
                assert not release_startup.is_set()

        asyncio.run(_drive())
        release_startup.set()

    monkeypatch.setattr(BuildLock, "request", fake_request)
    monkeypatch.setattr(
        "src.catalog_service.service.uvicorn.run",
        fake_uvicorn_run,
    )
    monkeypatch.setattr(
        "src.catalog_service.service.disable_quick_edit",
        lambda: False,
    )

    run_serve(settings)

    assert uvicorn_called.is_set()
    assert "startup" in request_calls
