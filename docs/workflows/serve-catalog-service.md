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

可选 `.env`：`FILE_BROWSER_BASE`（无尾斜杠）— File Browser 下载前缀，写入 HTTP playbook 的 `file_base`；未设则手册标明未配置。

## 行为

1. **先 listen，后台 startup**：`uvicorn` 监听后，FastAPI lifespan 用 daemon 线程触发 `trigger=startup` 全量 rebuild（不阻塞 HTTP）。已有 JSONL 时可立刻 search / 流式读（内容可为略旧）；缺失时 search/catalog **404**，`/health` 的 `building` 可反映重建中。startup 失败只打错误日志，不拖垮进程。
2. `WATCH_ENABLED`：监听 `*.material-tags.json` 增删改，debounce 后 rebuild；**排除目录**（`SCAN_EXCLUDE_DIR_NAMES`）内事件不触发 debounce。`WATCH_STARTUP_QUIET_SEC`（默认 10）：watcher 启动后静默期内忽略 tags 事件（不 schedule），避免启动噪声立刻再跑一轮全量；`0` 关闭静默。
3. `SCHEDULE_ENABLED`：每 `SCHEDULE_INTERVAL_SEC` 全量 rebuild。
4. 所有触发经 **BuildLock**：同时最多一个 build；忙时标记 pending，结束后再跑一轮。
5. CLI / watch / 定时 / HTTP rebuild **均调用同一** `build_catalog`：排除目录不扫；无白名单原媒体不写 JSONL，默认 purge 合法 orphan（契约「入索引条件」）；单次 build 内复用目录 listing 加速猜媒体。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | `{ status, version, root, building }` |
| GET | `/v1/catalog/search` | 关键词检索 JSON；找素材**主路径** |
| GET | `/v1/catalog` | `application/x-ndjson` 全量流式；导出/备份/小库调试；不存在 404 |
| GET | `/v1/catalog/meta` | path / size / mtime / line_count / last_build（含 `skipped` / `skipped_no_media` / `skipped_invalid` / `skipped_excluded` / `purged`） |
| POST | `/v1/catalog/rebuild` | 触发；忙则 202 queued；成功体含 written / skipped 及原因拆分（含 purged） |
| GET | `/v1/docs/llm-media-search-playbook` | 本服务 Agent 检索手册（`text/markdown`）；按**本次请求** `base_url` 注入 `api_base`，按可选 `FILE_BROWSER_BASE` 注入 `file_base`；缺模板文件 404 |

OpenAPI / Swagger：`http://127.0.0.1:8787/docs`（机器可读：`/openapi.json`）

### `GET /v1/catalog/search`

| 参数 | 默认 | 说明 |
|---|---|---|
| `q` | （必填） | 原始查询；按空白 / `,` / `，` 分词；拆完无 token → 400 |
| `limit` | 20 | 返回条数；`>100` 钳制为 100 |
| `offset` | 0 | 跳过前 N 条命中（≥0） |
| `path_prefix` | 未传 | 可选；可重复。相对 `CATALOG_ROOT` 的目录前缀（posix）。多值 **OR**；规范化后最多 20；未传 = 全库 |

**匹配与排序（写死）**

- 可检索字段：`title`、`description`、`keywords`（只读现有 JSONL 行，不改契约字段）。
- 路径关（可选）：仅看 `tags_path`。未设 `path_prefix` 则通过；否则须至少一个前缀满足**目录边界**（`tags_path == prefix` 或以 `prefix/` 开头；字面匹配、不做 casefold）。避免 `项目A` 误伤 `项目A备份`。
- 非法 `path_prefix`（含 `..`、或以 `/` 开头的绝对路径语义、规范化后超过 20 个）→ **400**；空串丢弃；全丢弃视为未设路径。
- 多词：**AND**（每个 token 都必须在上述字段的拼接文本中子串命中）。
- 大小写：对 haystack / needle 做 **casefold**（英文不区分大小写）。
- 加权（排序用，**响应不返回 score**）：keywords +3 / title +2 / description +1；同一 token 每字段最多计一次；分降序，同分按 `stem` 升序。
- 坏行跳过；catalog 文件不存在 → 404（与全量接口一致）。
- `total_matched`：路径关 ∩ 关键词命中的总数；分页基于该集合。

**响应（200）**：`{ query, tokens, limit, offset, total_matched, path_prefixes, items }`；`path_prefixes` 为规范化后生效列表（未传为 `[]`）；`items[]` 与 [catalog 行契约](../contracts/material-tags-catalog.md) 一致。

无命中：`items=[]`，`total_matched=0`，仍 200。

### Agent 两段式找素材（推荐）

面向「搜素材并给用户下载链接 + 固定回复格式」的完整一二三，见 **[llm-media-search-playbook.md](./llm-media-search-playbook.md)**，或 HTTP：`GET /v1/docs/llm-media-search-playbook`（返回已按本实例渲染的 Markdown：`api_base` = 本次请求根地址；可选 ENV `FILE_BROWSER_BASE` → `file_base`）。

1. **先定项目范围**：从用户口述或盘面目录得到相对 `CATALOG_ROOT` 的路径（如 `蜜梨的素材库`），写入一个或多个 `path_prefix`（多项目并查时重复该参数）。
2. 从用户口语提炼关键词，写入 `q`（可用空格或逗号多词收窄）。`q` 仍必填；不可只靠路径浏览。
3. `GET /v1/catalog/search?q=…&path_prefix=…&limit=20`，只读返回的 `items`；核对响应里的 `path_prefixes` 与 `total_matched`。
4. 精选 1～N 个 `stem`（及 `tags_path` / `media_guess`）；需要下载链时按 playbook 用 `file_base` + 分段编码 `media_guess` 自拼。
5. 若不满意：改 `path_prefix`、改写 `q`，或增大 `offset` 翻页（数据不变时翻页结果不与上一页重复）。
6. catalog 缺失 404 时：运维侧 `POST /v1/catalog/rebuild` 或检查 `CATALOG_ROOT`（找素材 Agent **勿**自行 rebuild，见 playbook）。路径写错导致 0 命中时，对照回显的 `path_prefixes` 与盘面相对路径，而非当成服务故障。

不必为找片拉全量 `GET /v1/catalog`（全量仍可用于导出与调试）。机器可读契约：`/openapi.json`（Swagger：`/docs`）。

## 验收

```bash
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/v1/catalog/meta
curl -s 'http://127.0.0.1:8787/v1/catalog/search?q=api&limit=5'
curl -s --get 'http://127.0.0.1:8787/v1/catalog/search' \
  --data-urlencode 'q=图' \
  --data-urlencode 'path_prefix=蜜梨的素材库' \
  --data-urlencode 'limit=20'
curl -s --get 'http://127.0.0.1:8787/v1/catalog/search' \
  --data-urlencode 'q=图' \
  --data-urlencode 'path_prefix=蜜梨的素材库' \
  --data-urlencode 'path_prefix=项目A'
curl -s http://127.0.0.1:8787/v1/catalog | head
curl -s -X POST http://127.0.0.1:8787/v1/catalog/rebuild
```

## 测试

```bash
.venv/bin/python -m pytest tests/src/catalog_service/test_api.py tests/src/catalog_service/test_search.py -q
```
