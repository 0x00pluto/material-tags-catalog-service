# 常驻 catalog 索引服务

同时启动：文件监听（debounce）、定时全量兜底、FastAPI HTTP。

## 入口

```bash
cd <本工作区>
cp .env.example .env   # 设置 CATALOG_ROOT
.venv/bin/python scripts/catalog_service/serve.py
```

命令行覆盖 root：

```bash
.venv/bin/python scripts/catalog_service/serve.py --root /path/to/media-library --host 127.0.0.1 --port 8787
```

Windows：`.venv\Scripts\python.exe scripts\catalog_service\serve.py`

## 局域网访问

默认 `HOST=127.0.0.1` 仅本机可访问。需要局域网访问时：

1. `.env` 设 `HOST=0.0.0.0`，或启动加 `--host 0.0.0.0`。
2. 重启后日志应出现 `serving host=0.0.0.0`。
3. 用 `http://<服务器局域网IP>:8787/health` 验活。
4. 不通时检查系统防火墙是否放行 `PORT`（默认 `8787`）。

见 [faqs/windows-lan-access-and-console-garbled.md](../faqs/windows-lan-access-and-console-garbled.md)。

## 行为

1. 启动时可先跑一轮 build（保证有索引可读）。
2. `WATCH_ENABLED`：监听 `*.material-tags.json` 增删改，debounce 后 rebuild。
3. `SCHEDULE_ENABLED`：每 `SCHEDULE_INTERVAL_SEC` 全量 rebuild。
4. 所有触发经 **BuildLock**：同时最多一个 build；忙时标记 pending，结束后再跑一轮。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | `{ status, version, root, building }` |
| GET | `/v1/catalog` | `application/x-ndjson` 流式；不存在 404 |
| GET | `/v1/catalog/meta` | path / size / mtime / line_count / last_build |
| POST | `/v1/catalog/rebuild` | 触发；忙则 202 queued |

OpenAPI：`http://127.0.0.1:8787/docs`

## 验收

```bash
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/v1/catalog/meta
curl -s http://127.0.0.1:8787/v1/catalog | head
curl -s -X POST http://127.0.0.1:8787/v1/catalog/rebuild
```

## 测试

```bash
.venv/bin/python -m pytest tests/src/catalog_service/test_api.py -q
```
