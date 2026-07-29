"""服务运行时：挂载 API + watch + schedule。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from src.catalog_service.api import create_app
from src.catalog_service.build_lock import BuildLock
from src.catalog_service.builder import build_catalog
from src.catalog_service.config import Settings
from src.catalog_service.scheduler import IntervalScheduler
from src.catalog_service.state import AppState
from src.catalog_service.watcher import CatalogWatcher
from src.catalog_service._version import __version__

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def run_serve(settings: Settings) -> None:
    configure_logging()
    logger.info("catalog-service version=%s", __version__)
    root = settings.catalog_root
    out = settings.resolved_out()
    if not root.is_dir():
        raise FileNotFoundError(f"CATALOG_ROOT 不存在或不是目录: {root}")

    build_lock = BuildLock()
    state = AppState()

    def run_build(trigger: str):
        result = build_catalog(root, out, trigger=trigger)
        state.record_build(result)
        return result

    # 启动先建一轮，保证 HTTP 可读
    try:
        build_lock.request("startup", run_build)
    except Exception:  # noqa: BLE001
        logger.exception("startup build failed; continuing")

    watcher: CatalogWatcher | None = None
    scheduler: IntervalScheduler | None = None

    if settings.watch_enabled:

        def on_watch() -> None:
            build_lock.request("watch", run_build)

        watcher = CatalogWatcher(
            root,
            debounce_sec=settings.watch_debounce_sec,
            on_change=on_watch,
        )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        nonlocal scheduler
        if watcher is not None:
            watcher.start()
        if settings.schedule_enabled:

            def on_tick() -> None:
                build_lock.request("timer", run_build)

            scheduler = IntervalScheduler(
                settings.schedule_interval_sec,
                on_tick,
            )
            await scheduler.start()
        yield
        if watcher is not None:
            watcher.stop()
        if scheduler is not None:
            await scheduler.stop()

    app = create_app(
        root=root,
        out=out,
        build_lock=build_lock,
        state=state,
        lifespan=lifespan,
    )

    logger.info(
        "serving host=%s port=%s root=%s out=%s",
        settings.host,
        settings.port,
        root,
        out,
    )
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        use_colors=False,
    )
