"""FastAPI 路由。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from src.catalog_service.build_lock import BuildLock
from src.catalog_service.builder import build_catalog
from src.catalog_service.playbook_docs import (
    render_playbook,
    resolve_playbook_markdown_path,
)
from src.catalog_service.search import (
    PATH_PREFIX_MAX,
    PathPrefixError,
    normalize_path_prefixes,
    search_catalog,
    tokenize_query,
)
from src.catalog_service.state import AppState
from src.catalog_service._version import __version__

_SEARCH_LIMIT_MAX = 100
_SEARCH_LIMIT_DEFAULT = 20


class CatalogItem(BaseModel):
    """catalog JSONL 一行的 search 视图（不含 score；省略 subtitle 全文）。"""

    stem: str
    tags_path: str
    media_guess: str | None = None
    schema_version: str | None = None
    generated_at: str | None = None
    title: str = ""
    description: str = ""
    keywords: str = ""
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    aspect_ratio: str | None = None
    orientation: str | None = None


class CatalogSearchResponse(BaseModel):
    """GET /v1/catalog/search 响应。"""

    query: str
    tokens: list[str]
    limit: int
    offset: int
    total_matched: int
    path_prefixes: list[str] = Field(
        default_factory=list,
        description="规范化后生效的 path_prefix；未传为 []",
    )
    items: list[CatalogItem] = Field(default_factory=list)


def create_app(
    *,
    root: Path,
    out: Path,
    build_lock: BuildLock,
    state: AppState,
    lifespan: Callable | None = None,
    exclude_dir_names: frozenset[str] | None = None,
    purge_orphan_tags: bool = True,
    playbook_path: Path | None = None,
    file_browser_base: str | None = None,
) -> FastAPI:
    kwargs: dict[str, Any] = {
        "title": "Material Tags Catalog Service",
        "version": __version__,
    }
    if lifespan is not None:
        kwargs["lifespan"] = lifespan

    app = FastAPI(**kwargs)
    exclude_set = exclude_dir_names if exclude_dir_names is not None else frozenset()

    def run_build(trigger: str):
        result = build_catalog(
            root,
            out,
            trigger=trigger,
            exclude_dir_names=exclude_set,
            purge_orphan_tags=purge_orphan_tags,
        )
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
            "对当前 catalog JSONL 做多词 AND 子串匹配"
            "（title / description / keywords / subtitle），"
            "按字段加权排序后返回 top K。"
            "匹配对英文字段使用 casefold；响应不含 score；items[] 省略 subtitle。"
            "可选重复 query 参数 path_prefix：相对 CATALOG_ROOT 的目录前缀，"
            "仅过滤 tags_path（目录边界：等于或 prefix/ 开头；多值 OR；最多 "
            f"{PATH_PREFIX_MAX} 个；含 .. 或绝对路径 → 400）。"
            "找素材推荐：先定项目 path_prefix → 再写 q → search → 精选 stem；"
            "可用 offset 翻页，或改写 q / path_prefix。"
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
        path_prefix: Annotated[
            list[str] | None,
            Query(
                description=(
                    "可选；相对 CATALOG_ROOT 的目录前缀（可重复，OR）。"
                    f"仅匹配 tags_path 目录边界；规范化后最多 {PATH_PREFIX_MAX} 个；"
                    "含 .. 或以 / 开头 → 400。未传则全库检索。"
                ),
            ),
        ] = None,
    ) -> CatalogSearchResponse:
        tokens = tokenize_query(q)
        if not tokens:
            raise HTTPException(
                status_code=400,
                detail="q must contain at least one non-empty token",
            )
        try:
            path_prefixes = normalize_path_prefixes(path_prefix)
        except PathPrefixError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not out.is_file():
            raise HTTPException(status_code=404, detail="catalog not found")

        effective_limit = min(limit, _SEARCH_LIMIT_MAX)
        result = search_catalog(
            out,
            tokens,
            limit=effective_limit,
            offset=offset,
            path_prefixes=path_prefixes,
        )
        return CatalogSearchResponse(
            query=q,
            tokens=tokens,
            limit=effective_limit,
            offset=offset,
            total_matched=result.total_matched,
            path_prefixes=path_prefixes,
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

    @app.get(
        "/v1/docs/llm-media-search-playbook",
        summary="LLM 媒体检索 playbook（Markdown）",
        tags=["docs"],
        description=(
            "返回本服务 Agent 检索手册（text/markdown）。"
            "按本次请求的 base URL 注入 api_base；可选 FILE_BROWSER_BASE 注入 file_base。"
        ),
        response_class=Response,
        responses={
            200: {
                "content": {"text/markdown": {"schema": {"type": "string"}}},
                "description": "playbook Markdown（已按本实例渲染）",
            },
            404: {"description": "playbook 文件未打包或不存在"},
        },
    )
    def get_llm_media_search_playbook(request: Request) -> Response:
        path = (
            playbook_path
            if playbook_path is not None
            else resolve_playbook_markdown_path()
        )
        if path is None or not path.is_file():
            raise HTTPException(status_code=404, detail="playbook not found")
        template = path.read_text(encoding="utf-8")
        api_base = str(request.base_url).rstrip("/")
        body = render_playbook(
            template,
            api_base=api_base,
            file_base=file_browser_base,
        )
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
        )

    return app
