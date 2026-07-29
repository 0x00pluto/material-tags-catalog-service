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

    rebuild = client.post("/v1/catalog/rebuild")
    assert rebuild.status_code == 200
    assert rebuild.json()["status"] == "ok"
    assert rebuild.json()["written"] == 1


def test_catalog_404(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    out = root / CATALOG_FILENAME
    app = create_app(root=root, out=out, build_lock=BuildLock(), state=AppState())
    client = TestClient(app)
    assert client.get("/v1/catalog").status_code == 404
