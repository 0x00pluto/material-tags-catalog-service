# 素材标签索引服务

贴着素材盘维护 `material-tags-catalog.jsonl`，HTTP 供 Agent 远程读取。

```bash
uv venv && uv pip install -r requirements.txt
cp .env.example .env   # 设置 CATALOG_ROOT

.venv/bin/python scripts/catalog_service/build.py --root /path/to/media
.venv/bin/python scripts/catalog_service/serve.py --root /path/to/media
```

默认 `127.0.0.1:8787`。Windows 用 `.venv\Scripts\python.exe`。

| 方法 | 路径 |
|---|---|
| GET | `/health` |
| GET | `/v1/catalog` |
| GET | `/v1/catalog/meta` |
| POST | `/v1/catalog/rebuild` |

便携包：Release 下 zip → 改 `.env` → 双击 `start`。发版见 [portable-dist-ci](docs/workflows/portable-dist-ci.md)。文档索引：[doc_index](docs/doc_index.md)。
