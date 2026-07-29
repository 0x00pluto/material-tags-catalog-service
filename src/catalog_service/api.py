"""FastAPI 路由。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from src.catalog_service.build_lock import BuildLock
from src.catalog_service.builder import build_catalog
from src.catalog_service.state import AppState
from src.catalog_service._version import __version__


def create_app(
    *,
    root: Path,
    out: Path,
    build_lock: BuildLock,
    state: AppState,
    lifespan: Callable | None = None,
) -> FastAPI:
    kwargs: dict[str, Any] = {
        "title": "Material Tags Catalog Service",
        "version": __version__,
    }
    if lifespan is not None:
        kwargs["lifespan"] = lifespan

    app = FastAPI(**kwargs)

    def run_build(trigger: str):
        result = build_catalog(root, out, trigger=trigger)
        state.record_build(result)
        return result

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "root": str(root),
            "building": build_lock.building,
        }

    @app.get("/v1/catalog")
    def get_catalog() -> StreamingResponse:
        if not out.is_file():
            raise HTTPException(status_code=404, detail="catalog not found")

        def iter_file():
            with out.open("rb") as fh:
                while True:
                    chunk = fh.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            iter_file(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'inline; filename="{out.name}"'},
        )

    @app.get("/v1/catalog/meta")
    def get_meta() -> dict[str, Any]:
        exists = out.is_file()
        size = out.stat().st_size if exists else 0
        mtime = out.stat().st_mtime if exists else None
        line_count = 0
        if exists:
            with out.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        line_count += 1
        return {
            "path": str(out),
            "exists": exists,
            "size": size,
            "mtime": mtime,
            "line_count": line_count,
            "last_build": state.last_build(),
        }

    @app.post("/v1/catalog/rebuild")
    def rebuild() -> JSONResponse:
        result, queued = build_lock.request("http", run_build)
        if queued:
            return JSONResponse(
                status_code=202,
                content={"status": "queued", "building": True},
            )
        assert result is not None
        return JSONResponse(
            status_code=200,
            content={"status": "ok", **result.to_dict()},
        )

    return app
