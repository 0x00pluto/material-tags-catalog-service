"""FastAPI TestClient 测试。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.catalog_service.api import create_app
from src.catalog_service.build_lock import BuildLock
from src.catalog_service.builder import build_catalog
from src.catalog_service.models import CATALOG_FILENAME, tags_filename_for_stem
from src.catalog_service.state import AppState

SAMPLE = {
    "schema_version": "1",
    "generated_at": "2026-07-29T09:00:00+08:00",
    "title": "api标题",
    "description": "api描述",
    "keywords": "api, test",
}


def _setup_lib(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "media"
    root.mkdir()
    tags = root / tags_filename_for_stem("clip")
    tags.write_text(json.dumps(SAMPLE, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "clip.mp4").write_bytes(b"x")
    out = root / CATALOG_FILENAME
    return root, out


def test_health_and_catalog(tmp_path: Path) -> None:
    root, out = _setup_lib(tmp_path)
    lock = BuildLock()
    state = AppState()

    def run_build(trigger: str):
        result = build_catalog(root, out, trigger=trigger)
        state.record_build(result)
        return result

    run_build("test")
    app = create_app(root=root, out=out, build_lock=lock, state=state)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["root"] == str(root)
    assert "version" in health.json()
    assert isinstance(health.json()["version"], str)
    assert health.json()["version"]  # non-empty

    catalog = client.get("/v1/catalog")
    assert catalog.status_code == 200
    assert "application/x-ndjson" in catalog.headers["content-type"]
    row = json.loads(catalog.text.strip().splitlines()[0])
    assert row["stem"] == "clip"

    meta = client.get("/v1/catalog/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["exists"] is True
    assert body["line_count"] == 1
    assert body["last_build"]["written"] == 1
    assert body["last_build"]["skipped"] == 0
    assert body["last_build"]["skipped_no_media"] == 0
    assert body["last_build"]["skipped_invalid"] == 0
    assert body["last_build"]["skipped_excluded"] == 0
    assert body["last_build"]["purged"] == 0

    rebuild = client.post("/v1/catalog/rebuild")
    assert rebuild.status_code == 200
    assert rebuild.json()["status"] == "ok"
    assert rebuild.json()["written"] == 1
    assert rebuild.json()["skipped_no_media"] == 0
    assert rebuild.json()["skipped_invalid"] == 0
    assert rebuild.json()["skipped_excluded"] == 0
    assert rebuild.json()["purged"] == 0


def test_catalog_404(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    out = root / CATALOG_FILENAME
    app = create_app(root=root, out=out, build_lock=BuildLock(), state=AppState())
    client = TestClient(app)
    assert client.get("/v1/catalog").status_code == 404


def _client_with_catalog(tmp_path: Path) -> TestClient:
    root, out = _setup_lib(tmp_path)
    lock = BuildLock()
    state = AppState()
    build_catalog(root, out, trigger="test")
    app = create_app(root=root, out=out, build_lock=lock, state=state)
    return TestClient(app)


def test_search_ok(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    resp = client.get("/v1/catalog/search", params={"q": "api"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "api"
    assert body["tokens"] == ["api"]
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total_matched"] == 1
    assert body["path_prefixes"] == []
    assert len(body["items"]) == 1
    assert body["items"][0]["stem"] == "clip"
    assert "score" not in body["items"][0]
    # V1 样例：媒体元数据键存在且为 null
    item = body["items"][0]
    assert item["width"] is None
    assert item["height"] is None
    assert item["duration_s"] is None
    assert item["aspect_ratio"] is None
    assert item["orientation"] is None


def test_search_returns_v2_media_meta(tmp_path: Path) -> None:
    root = tmp_path / "media"
    root.mkdir()
    sample_v2 = {
        "schema_version": "2",
        "generated_at": "2026-07-30T11:05:03+08:00",
        "title": "玄关衣帽鞋凳特写",
        "description": "竖屏产品特写",
        "keywords": "玄关衣帽架, 鞋凳",
        "width": 1080,
        "height": 1920,
        "duration_s": 11.01,
        "aspect_ratio": "9:16",
        "orientation": "竖屏",
    }
    tags = root / tags_filename_for_stem("v2clip")
    tags.write_text(json.dumps(sample_v2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "v2clip.mp4").write_bytes(b"x")
    out = root / CATALOG_FILENAME
    build_catalog(root, out, trigger="test")
    app = create_app(root=root, out=out, build_lock=BuildLock(), state=AppState())
    client = TestClient(app)

    resp = client.get("/v1/catalog/search", params={"q": "玄关", "limit": 5})
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["schema_version"] == "2"
    assert item["width"] == 1080
    assert item["height"] == 1920
    assert item["duration_s"] == 11.01
    assert item["aspect_ratio"] == "9:16"
    assert item["orientation"] == "竖屏"


def test_search_empty_q_400(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    assert client.get("/v1/catalog/search", params={"q": ""}).status_code == 400
    assert client.get("/v1/catalog/search", params={"q": "  ,， "}).status_code == 400
    assert client.get("/v1/catalog/search").status_code == 422


def test_search_no_hit(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    resp = client.get("/v1/catalog/search", params={"q": "绝不存在的词xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_matched"] == 0
    assert body["items"] == []


def test_search_404_missing_catalog(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    out = root / CATALOG_FILENAME
    app = create_app(root=root, out=out, build_lock=BuildLock(), state=AppState())
    client = TestClient(app)
    assert (
        client.get("/v1/catalog/search", params={"q": "anything"}).status_code == 404
    )


def test_search_limit_clamped(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    resp = client.get("/v1/catalog/search", params={"q": "api", "limit": 500})
    assert resp.status_code == 200
    assert resp.json()["limit"] == 100


def test_search_path_prefix(tmp_path: Path) -> None:
    root = tmp_path / "media"
    root.mkdir()
    # 同关键词、不同项目目录
    for stem, sub in (("a1", "项目A"), ("b1", "项目B"), ("bak", "项目A备份")):
        d = root / sub
        d.mkdir(parents=True, exist_ok=True)
        tags = d / tags_filename_for_stem(stem)
        tags.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "title": "图素材",
                    "description": "d",
                    "keywords": "图",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (d / f"{stem}.mp4").write_bytes(b"x")
    out = root / CATALOG_FILENAME
    build_catalog(root, out, trigger="test")
    client = TestClient(
        create_app(root=root, out=out, build_lock=BuildLock(), state=AppState())
    )

    single = client.get(
        "/v1/catalog/search",
        params=[("q", "图"), ("path_prefix", "项目A")],
    )
    assert single.status_code == 200
    body = single.json()
    assert body["path_prefixes"] == ["项目A"]
    assert body["total_matched"] == 1
    assert body["items"][0]["stem"] == "a1"

    multi = client.get(
        "/v1/catalog/search",
        params=[("q", "图"), ("path_prefix", "项目A"), ("path_prefix", "项目B")],
    )
    assert multi.status_code == 200
    mbody = multi.json()
    assert mbody["path_prefixes"] == ["项目A", "项目B"]
    assert mbody["total_matched"] == 2
    assert {i["stem"] for i in mbody["items"]} == {"a1", "b1"}


def test_search_path_prefix_invalid_400(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    assert (
        client.get(
            "/v1/catalog/search",
            params=[("q", "api"), ("path_prefix", "..")],
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/v1/catalog/search",
            params=[("q", "api"), ("path_prefix", "/abs")],
        ).status_code
        == 400
    )
    too_many = [("q", "api")] + [("path_prefix", f"p{i}") for i in range(21)]
    assert client.get("/v1/catalog/search", params=too_many).status_code == 400


def test_search_path_prefix_still_requires_q(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    assert (
        client.get(
            "/v1/catalog/search",
            params=[("q", "  "), ("path_prefix", "项目A")],
        ).status_code
        == 400
    )


def test_openapi_includes_search(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    schema = client.get("/openapi.json").json()
    assert "/v1/catalog/search" in schema["paths"]
    search_get = schema["paths"]["/v1/catalog/search"]["get"]
    assert "CatalogSearchResponse" in schema["components"]["schemas"]
    params = {p["name"] for p in search_get["parameters"]}
    assert {"q", "limit", "offset", "path_prefix"} <= params
    props = schema["components"]["schemas"]["CatalogSearchResponse"]["properties"]
    assert "path_prefixes" in props


def test_playbook_http_ok(tmp_path: Path) -> None:
    root, out = _setup_lib(tmp_path)
    playbook = tmp_path / "playbook.md"
    playbook.write_text(
        "# hello\napi={{api_base}}\nfile={{file_base}}\n",
        encoding="utf-8",
    )
    app = create_app(
        root=root,
        out=out,
        build_lock=BuildLock(),
        state=AppState(),
        playbook_path=playbook,
        file_browser_base="http://files.example/share",
    )
    client = TestClient(app)
    resp = client.get("/v1/docs/llm-media-search-playbook")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "api=http://testserver" in resp.text
    assert "file=http://files.example/share" in resp.text
    assert "{{api_base}}" not in resp.text


def test_playbook_http_404(tmp_path: Path) -> None:
    root, out = _setup_lib(tmp_path)
    missing = tmp_path / "no-such.md"
    app = create_app(
        root=root,
        out=out,
        build_lock=BuildLock(),
        state=AppState(),
        playbook_path=missing,
    )
    client = TestClient(app)
    resp = client.get("/v1/docs/llm-media-search-playbook")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "playbook not found"


def test_playbook_http_file_base_unset(tmp_path: Path) -> None:
    root, out = _setup_lib(tmp_path)
    playbook = tmp_path / "playbook.md"
    playbook.write_text("fb={{file_base}}\n", encoding="utf-8")
    app = create_app(
        root=root,
        out=out,
        build_lock=BuildLock(),
        state=AppState(),
        playbook_path=playbook,
        file_browser_base=None,
    )
    client = TestClient(app)
    resp = client.get("/v1/docs/llm-media-search-playbook")
    assert resp.status_code == 200
    assert "未配置 FILE_BROWSER_BASE" in resp.text
    assert "huanyuan-share" not in resp.text
    assert "192.168.0.8:8787" not in resp.text


def test_playbook_http_resolves_repo_default(tmp_path: Path) -> None:
    """未注入路径时，从仓库 docs/ 解析真实 playbook 并渲染。"""
    client = _client_with_catalog(tmp_path)
    resp = client.get("/v1/docs/llm-media-search-playbook")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "LLM Playbook" in resp.text
    assert "http://testserver/v1/catalog/search" in resp.text
    assert "{{api_base}}" not in resp.text
    # 可选技能安装指针可出现；禁止写死技能默认盘前缀 / 内网 IP
    assert "huanyuan-share" not in resp.text
    assert "192.168.0.8" not in resp.text
    schema = client.get("/openapi.json").json()
    assert "/v1/docs/llm-media-search-playbook" in schema["paths"]


def test_resolve_playbook_markdown_path() -> None:
    from src.catalog_service.playbook_docs import resolve_playbook_markdown_path

    path = resolve_playbook_markdown_path()
    assert path is not None
    assert path.is_file()
    assert path.name == "llm-media-search-playbook.md"


def test_render_playbook() -> None:
    from src.catalog_service.playbook_docs import FILE_BASE_UNSET, render_playbook

    out = render_playbook(
        "a={{api_base}} f={{file_base}}",
        api_base="http://localhost:11777/",
        file_base=None,
    )
    assert out == f"a=http://localhost:11777 f={FILE_BASE_UNSET}"
    out2 = render_playbook(
        "{{api_base}}|{{file_base}}",
        api_base="http://x:1",
        file_base="http://fb/share/",
    )
    assert out2 == "http://x:1|http://fb/share"


def test_normalize_file_browser_base_and_settings(tmp_path: Path) -> None:
    from src.catalog_service.config import Settings
    from src.catalog_service.playbook_docs import normalize_file_browser_base

    assert normalize_file_browser_base(None) is None
    assert normalize_file_browser_base("  ") is None
    assert normalize_file_browser_base("http://fb/share/") == "http://fb/share"
    assert normalize_file_browser_base("http://fb/share///") == "http://fb/share"

    root = tmp_path / "media"
    root.mkdir()
    settings = Settings(
        CATALOG_ROOT=root,
        FILE_BROWSER_BASE=" http://fb.example/files/ ",
    )
    assert settings.file_browser_base == "http://fb.example/files"
    settings_empty = Settings(CATALOG_ROOT=root, FILE_BROWSER_BASE="  ")
    assert settings_empty.file_browser_base is None
