# 素材标签索引服务 — Material Tags Catalog Service

贴着素材盘运行的轻量索引服务：监听 + 定时重建 `material-tags-catalog.jsonl`，并用 FastAPI 对外提供可读、可触发的 HTTP 接口。

**本仓不是打标引擎**：不写视觉/多模态标签，只消费约定格式的 `*.material-tags.json`。

## 开始工作前

1. 先读 [`docs/doc_index.md`](./docs/doc_index.md) 找到相关文档，再动手。
2. 改动落进既有目录语义（见下表），不新增平级顶层目录。
3. 新增或改动文档后，登记进 `docs/doc_index.md`。
4. 检索本仓代码结构时，优先用 Codebase Memory MCP（`search_graph` / `trace_path` 等）。

## 目录约定

| 目录 | 用途 | 入库 |
|---|---|---|
| `src/` | 业务逻辑；`src/catalog_service/` | 是 |
| `scripts/` | CLI 入口；含 `catalog_service/` 与 `packaging/` | 是 |
| `tests/` | 测试，结构镜像 `src/` | 是 |
| `docs/` | 开发文档（契约 / workflow / FAQ） | 是 |
| `specs/` | 产品规格；`specs/prds/` 存放 PRD | 是 |
| `upgrades/` | 发版说明：tag ↔ `vX.Y.Z.md`，供 GitHub Release 正文 | 是 |
| `temp/` | 中间产物 / 打包 scratch | 否 |
| `dist/` | PyInstaller 等构建产物 | 否 |

正式索引源永远是客户/服务器素材盘（`CATALOG_ROOT`）。本仓不设 `cache/`、`output/`。`upgrades/` 与 `specs/prds/` **不**登记进 `docs/doc_index.md`。

## 文档约定

| 路径 | 内容 |
|---|---|
| `docs/doc_index.md` | 技术文档唯一入口索引 |
| `specs/prds/` | PRD（`prd-{五位序号}-{feature-slug}.md`） |
| `docs/contracts/` | 数据契约 |
| `docs/workflows/` | 可复跑动作 |
| `docs/faqs/` | 踩坑一篇一文件 |

## 环境

Python **3.12+**，用 **UV** 管理，虚拟环境在本仓 `.venv/`：

```bash
uv venv && uv pip install -r requirements.txt
.venv/bin/python scripts/catalog_service/build.py --help
.venv/bin/python scripts/catalog_service/serve.py --help
```

一律显式用 `.venv/bin/python`（Windows：`.venv\Scripts\python.exe`）。本仓使用**本仓** `.venv`，不借用兄弟项目虚拟环境，不硬编码兄弟仓 `sys.path`。

测试框架：**pytest**。

```bash
.venv/bin/python -m pytest -q
```

## 环境变量

见 [`.env.example`](./.env.example)。关键项：`CATALOG_ROOT`（必填）、`HOST`/`PORT`、`WATCH_*`、`SCHEDULE_*`。

## 依赖的兄弟项目

| 项目 | 关系 |
|---|---|
| [`../Codex/多媒体资源打标/`](../Codex/多媒体资源打标/) | 上游生产者：写 `*.material-tags.json`；本仓只认契约格式 |
| [`../Codex/FileBrowser资源打标/`](../Codex/FileBrowser资源打标/) | 旁路编排；本仓不依赖 |

## 团队 Cursor 命令

本地命令见 [`.cursor/commands/team/`](./.cursor/commands/team/)（`/team:product-manager`、`/team:prd-accept`、`/team:python-engineer`、`/team:test-enginer`）。母版维护于 Obsidian Vibecoding「团队成员」，安装 SOP 见其使用说明。
