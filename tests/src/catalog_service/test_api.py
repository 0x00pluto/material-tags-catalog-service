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

    rebuild = client.post("/v1/catalog/rebuild")
    assert rebuild.status_code == 200
    assert rebuild.json()["status"] == "ok"
    assert rebuild.json()["written"] == 1
    assert rebuild.json()["skipped_no_media"] == 0
    assert rebuild.json()["skipped_invalid"] == 0


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


def test_openapi_includes_search(tmp_path: Path) -> None:
    client = _client_with_catalog(tmp_path)
    schema = client.get("/openapi.json").json()
    assert "/v1/catalog/search" in schema["paths"]
    search_get = schema["paths"]["/v1/catalog/search"]["get"]
    assert "CatalogSearchResponse" in schema["components"]["schemas"]
    params = {p["name"] for p in search_get["parameters"]}
    assert {"q", "limit", "offset"} <= params
