# 常驻 catalog 索引服务

同时启动：文件监听（debounce）、定时全量兜底、FastAPI HTTP。

## 入口

开发联调（推荐，仓库根目录执行）：

```bash
./scripts/catalog_service/dev-serve.sh
# 或指定素材盘：
./scripts/catalog_service/dev-serve.sh /path/to/media-library
```

未配置 `CATALOG_ROOT` / `.env` 时，脚本会用 `temp/dev-media` 自动放一份样例标签+mp4。浏览器打开 `http://127.0.0.1:8787/docs`。

正式 / 手动：

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

单元测试一键：

```bash
./scripts/catalog_service/dev-test.sh
```

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
5. CLI / watch / 定时 / HTTP rebuild **均调用同一** `build_catalog`：无白名单原媒体的标签不写入 JSONL（契约「入索引条件」）。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | `{ status, version, root, building }` |
| GET | `/v1/catalog/search` | 关键词检索 JSON；找素材**主路径** |
| GET | `/v1/catalog` | `application/x-ndjson` 全量流式；导出/备份/小库调试；不存在 404 |
| GET | `/v1/catalog/meta` | path / size / mtime / line_count / last_build（含 `skipped` / `skipped_no_media` / `skipped_invalid`） |
| POST | `/v1/catalog/rebuild` | 触发；忙则 202 queued；成功体含 written / skipped 及原因拆分 |

OpenAPI / Swagger：`http://127.0.0.1:8787/docs`（机器可读：`/openapi.json`）

### `GET /v1/catalog/search`

| 参数 | 默认 | 说明 |
|---|---|---|
| `q` | （必填） | 原始查询；按空白 / `,` / `，` 分词；拆完无 token → 400 |
| `limit` | 20 | 返回条数；`>100` 钳制为 100 |
| `offset` | 0 | 跳过前 N 条命中（≥0） |

**匹配与排序（写死）**

- 可检索字段：`title`、`description`、`keywords`（只读现有 JSONL 行，不改契约字段）。
- 多词：**AND**（每个 token 都必须在上述字段的拼接文本中子串命中）。
- 大小写：对 haystack / needle 做 **casefold**（英文不区分大小写）。
- 加权（排序用，**响应不返回 score**）：keywords +3 / title +2 / description +1；同一 token 每字段最多计一次；分降序，同分按 `stem` 升序。
- 坏行跳过；catalog 文件不存在 → 404（与全量接口一致）。

**响应（200）**：`{ query, tokens, limit, offset, total_matched, items }`；`items[]` 与 [catalog 行契约](../contracts/material-tags-catalog.md) 一致。

无命中：`items=[]`，`total_matched=0`，仍 200。

### Agent 两段式找素材（推荐）

1. 从用户口语提炼关键词，写入 `q`（可用空格或逗号多词收窄）。
2. `GET /v1/catalog/search?q=…&limit=20`，只读返回的 `items`（参考 `total_matched`）。
3. 精选 1～N 个 `stem`（及 `tags_path` / `media_guess`）。
4. 若不满意：改写 `q`，或增大 `offset` 翻页（数据不变时翻页结果不与上一页重复）。
5. catalog 缺失 404 时：先 `POST /v1/catalog/rebuild` 或检查 `CATALOG_ROOT`。

不必为找片拉全量 `GET /v1/catalog`（全量仍可用于导出与调试）。

## 验收

```bash
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/v1/catalog/meta
curl -s 'http://127.0.0.1:8787/v1/catalog/search?q=api&limit=5'
curl -s http://127.0.0.1:8787/v1/catalog | head
curl -s -X POST http://127.0.0.1:8787/v1/catalog/rebuild
```

## 测试

```bash
.venv/bin/python -m pytest tests/src/catalog_service/test_api.py tests/src/catalog_service/test_search.py -q
```
