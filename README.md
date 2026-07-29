# 素材标签索引服务

轻量 HTTP 索引服务：自动维护素材盘上的 `material-tags-catalog.jsonl`，供 Agent / 大模型远程读取。

## 安装

```bash
cd materialTagsCatalogService
uv venv && uv pip install -r requirements.txt
cp .env.example .env   # 编辑 CATALOG_ROOT
```

Windows 将下文 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。

## 一次性合并

```bash
.venv/bin/python scripts/catalog_service/build.py --root /path/to/media-library
```

## 常驻服务（watch + 定时 + HTTP）

```bash
# 读取 .env 中 CATALOG_ROOT 等
.venv/bin/python scripts/catalog_service/serve.py

# 或命令行覆盖
.venv/bin/python scripts/catalog_service/serve.py --root /path/to/media-library
```

默认绑定 `127.0.0.1:8787`。开发可开 `/docs`。

## API 摘要

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/v1/catalog` | 流式 JSONL |
| GET | `/v1/catalog/meta` | 索引元信息 / 上次 build 统计 |
| POST | `/v1/catalog/rebuild` | 触发重建（忙则排队，202） |

MVP 默认不鉴权，仅建议内网部署。

## 测试

```bash
.venv/bin/python -m pytest -q
```

## 便携分发（Win / Mac）

内部同事无需装 Python：从 GitHub Release 下载对应平台 zip，解压后改 `.env` 里的 `CATALOG_ROOT`，双击 `start` 即可。发版与用法见 [`docs/workflows/portable-dist-ci.md`](docs/workflows/portable-dist-ci.md)。

建议远程仓名：`material-tags-catalog-service`。版本与 Git tag（`vX.Y.Z`）由 CI 注入，本地默认 `0.0.0+local`；`GET /health` 与 `--version` 可查看。

## 文档

见 [`docs/doc_index.md`](docs/doc_index.md)。产品需求：[`docs/prd-material-tags-catalog-service.md`](docs/prd-material-tags-catalog-service.md)。
