"""FastAPI 路由。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.catalog_service.build_lock import BuildLock
from src.catalog_service.builder import build_catalog
from src.catalog_service.search import search_catalog, tokenize_query
from src.catalog_service.state import AppState
from src.catalog_service._version import __version__

_SEARCH_LIMIT_MAX = 100
_SEARCH_LIMIT_DEFAULT = 20


class CatalogItem(BaseModel):
    """catalog JSONL 一行（检索结果项；不含 score）。"""

    stem: str
    tags_path: str
    media_guess: str | None = None
    schema_version: str | None = None
    generated_at: str | None = None
    title: str = ""
    description: str = ""
    keywords: str = ""


class CatalogSearchResponse(BaseModel):
    """GET /v1/catalog/search 响应。"""

    query: str
    tokens: list[str]
    limit: int
    offset: int
    total_matched: int
    items: list[CatalogItem] = Field(default_factory=list)


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

    @app.get(
        "/v1/catalog/search",
        response_model=CatalogSearchResponse,
        summary="关键词检索 catalog",
        tags=["catalog"],
        description=(
            "对当前 catalog JSONL 做多词 AND 子串匹配（title / description / keywords），"
            "按字段加权排序后返回 top K。"
            "匹配对英文字段使用 casefold；响应不含 score。"
            "找素材主路径：构造 q → search → 精选 stem；可用 offset 翻页或改写 q。"
        ),
    )
    def search_catalog_endpoint(
        q: Annotated[
            str,
            Query(description="关键词；空白或中英文逗号分词；多词 AND"),
        ],
        limit: Annotated[
            int,
            Query(
                ge=1,
                description=f"默认 {_SEARCH_LIMIT_DEFAULT}，硬上限 {_SEARCH_LIMIT_MAX}（超出钳制）",
            ),
        ] = _SEARCH_LIMIT_DEFAULT,
        offset: Annotated[
            int,
            Query(ge=0, description="跳过前 N 条命中；默认 0"),
        ] = 0,
    ) -> CatalogSearchResponse:
        tokens = tokenize_query(q)
        if not tokens:
            raise HTTPException(
                status_code=400,
                detail="q must contain at least one non-empty token",
            )
        if not out.is_file():
            raise HTTPException(status_code=404, detail="catalog not found")

        effective_limit = min(limit, _SEARCH_LIMIT_MAX)
        result = search_catalog(
            out,
            tokens,
            limit=effective_limit,
            offset=offset,
        )
        return CatalogSearchResponse(
            query=q,
            tokens=tokens,
            limit=effective_limit,
            offset=offset,
            total_matched=result.total_matched,
            items=[CatalogItem.model_validate(row) for row in result.items],
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
