# PRD：素材标签索引服务（Material Tags Catalog Service）

| 项 | 内容 |
|---|---|
| 产品暂定名 | 素材标签索引服务 |
| 英文/仓名建议 | `material-tags-catalog-service`（或中文仓名自定，英文 slug 建议固定） |
| 版本 | v0.1（MVP）→ v1.0（可对外演示） |
| 文档日期 | 2026-07-29 |
| 关联仓 | `多媒体资源打标`（打标引擎）、`FileBrowser资源打标`（编排，非本仓职责） |

> 本文档可整份拷贝到新仓库使用。本仓仅作草稿存放，**未**登记进 `docs/doc_index.md`。

---

## 1. 背景与问题

### 1.1 现状

- 素材经打标后，盘上分散落盘为 `<stem>.material-tags.json`。
- 已有一次性合并工具，可生成 `material-tags-catalog.jsonl`，但：
  - 需人工/脚本触发，**无自动随盘更新**；
  - 大模型/Agent 往往要经 **File Browser 下载** 再读，链路长、易过期、不便远程用。

### 1.2 要解决的问题

1. 素材盘有新标签（或定时兜底）时，**自动维护**一份最新 JSONL 索引。
2. 通过 **HTTP** 直接拿到 JSONL（及元信息），供大模型/Agent **远程读取并回答**，减少「下载到本地再读」。
3. **Win / Mac 通用**，易调试、可独立部署；为后续单独售卖留边界。

### 1.3 非目标（本仓不做）

- 不做视觉/多模态打标、抽帧、转写、转码。
- 不替代 File Browser；不实现 File Browser 登录编排。
- 不对本仓（或打标仓）的开发用 `output/` 做「正式索引源」——正式源永远是**客户/服务器素材盘**。
- v0.1 不做向量库、全文搜索引擎、多租户 SaaS 控制台（可列为后续）。

---

## 2. 产品定位与边界

### 2.1 一句话

> 贴着素材盘运行的轻量索引服务：监听 + 定时重建 `material-tags-catalog.jsonl`，并用 FastAPI 对外提供可读、可触发的 HTTP 接口。

### 2.2 与兄弟产品关系

| 产品 | 职责 | 本仓关系 |
|---|---|---|
| 多媒体资源打标 | 写单条 `*.material-tags.json`；可选保留手动 `build_catalog` CLI | **上游生产者**；本仓只消费约定格式 |
| FileBrowser资源打标 | 拉盘、条件转码、协调打标、回传 | **旁路编排**；本仓不依赖它 |
| **本仓（索引服务）** | watch / cron / 写 JSONL / HTTP 提供索引 | **下游索引面** |

耦合方式：**只认契约文件格式**，不 import 打标仓的 evidence/ffmpeg/提示词。

### 2.3 可售卖映射（远期）

| 可卖包 | 内容 |
|---|---|
| A 打标引擎 | 现有「多媒体资源打标」 |
| B 索引服务 | 本仓（本 PRD） |
| （可选）C 编排 | FileBrowser 编排仓 |

---

## 3. 用户与场景

### 3.1 角色

| 角色 | 诉求 |
|---|---|
| 运维/开发 | 在素材机上装服务，配 root/端口，后台常驻 |
| Agent / 大模型调用方 | `GET` JSONL 或元信息，做检索回答 |
| 未来客户 IT | 改配置即可指向自己的素材盘，可选 API Key |

### 3.2 核心场景

1. **盘更新自动索引**：新打标文件落入素材盘 → debounce → rebuild → HTTP 立即可读新索引。
2. **定时兜底**：每 N 分钟全量扫一次，防止监听漏事件、网络盘抖动。
3. **Agent 远程读**：`GET /v1/catalog` 流式拿 JSONL，无需 File Browser 下载。
4. **人工强制重建**：`POST /v1/catalog/rebuild` 或 CLI `build`。
5. **健康检查**：部署脚本 / 监控打 `GET /health`。

---

## 4. 功能需求

### 4.1 P0（MVP 必须）

| ID | 功能 | 说明 |
|---|---|---|
| F1 | 扫描合并 | 递归扫描 `--root` 下 `*.material-tags.json`，跳过 catalog 自身文件名，写出 JSONL |
| F2 | 记录字段 | 与现有约定对齐（见 §6）：stem、tags_path、media_guess、schema_version、generated_at、title、description、keywords |
| F3 | 原子写 | 先写临时文件再 rename，避免读到半截 |
| F4 | 单条容错 | 坏 JSON/缺字段 skip 并记日志/计数，不中断整次 build |
| F5 | Watch 触发 | 监听 root 下标签文件增删改（及必要时目录事件），**debounce** 后 rebuild |
| F6 | 定时触发 | 可配置 cron 或 interval（如每 5/10 分钟）全量 rebuild |
| F7 | 互斥锁 | watch 与 timer 与手动 rebuild **同时最多一个 build**；排队或合并为一次 |
| F8 | FastAPI 提供索引 | 至少：健康检查、获取 JSONL、获取元信息、触发 rebuild |
| F9 | CLI | `serve`（起服务）、`build`（一次性）、`status`（可选） |
| F10 | 配置 | 环境变量 / `.env`：ROOT、OUT、HOST、PORT、debounce、interval、API_KEY（可先可选） |
| F11 | 跨平台 | Windows + macOS 路径、编码 UTF-8；文档给出两边启动方式 |
| F12 | 日志 | 结构化或清晰文本：触发原因、written/skipped、耗时、错误路径 |

### 4.2 P1（v1.0 建议）

| ID | 功能 | 说明 |
|---|---|---|
| F13 | API Key / Bearer | 读接口可公开或保护；rebuild 建议必须鉴权 |
| F14 | ETag / If-None-Match | 减少 Agent 重复拉全量 |
| F15 | 增量策略（可选） | 大盘全量慢时：按 mtime 增量合并（需设计清楚，可后置） |
| F16 | 查询辅助 | 如 `GET /v1/catalog/search?q=` 简单关键词过滤（内存或流式扫），非向量 |
| F17 | 系统服务说明 | launchd / Windows 服务或计划任务 + 常驻进程文档 |
| F18 | OpenAPI 示例 | `/docs` + 给 Cursor/Agent 的调用示例文案 |

### 4.3 P2（远期 / 商业化）

- 多 root（多素材库）、多 catalog 命名空间
- 管理 UI（可选 Tauri）
- 用量统计、许可证
- 与打标引擎打包成安装器

---

## 5. 技术栈（锁定建议）

| 层级 | 选型 | 理由 |
|---|---|---|
| 语言 | **Python 3.12+** | 与打标仓生态一致；文件/JSON 成熟；好调试 |
| 包管理 | **UV** + `requirements.txt`（或后续 `pyproject.toml`） | 与现有仓一致 |
| HTTP | **FastAPI + Uvicorn** | 自带 `/docs`，IDE 可断点调试 |
| CLI | **Typer**（或先 argparse，建议 Typer） | `serve` / `build` 子命令清晰 |
| 文件监听 | **watchdog** | Win/macOS 递归监听成熟 |
| 定时 | **APScheduler** 或 asyncio 自管 interval | 简单 interval 即可；不必上 Celery |
| 配置 | **pydantic-settings** + `.env` | 与 FastAPI 同生态 |
| 测试 | **unittest** 或 **pytest** | 与打标仓可对齐 unittest，新仓用 pytest 也可，定一种 |
| 禁止（MVP） | Electron/Tauri、Node 重写核心、数据库、Redis、Docker 强依赖 | 保持可卖前的轻量；Docker 可作 P1 文档可选项 |

**合并逻辑**：从「多媒体资源打标」的 `build_catalog` / `catalog_record` **移植或抽成薄模块进本仓**（推荐本仓自包含一份，避免运行时依赖兄弟仓路径）。契约与字段保持一致；`schema_version` 同步演进。

---

## 6. 数据契约（与上游对齐）

### 6.1 输入：单条标签文件

- 匹配：`**/*.material-tags.json`
- 不扫描：输出 catalog 文件名（默认 `material-tags-catalog.jsonl`）
- 必要内容字段：`title`、`description`、`keywords`
- 可选元数据：`schema_version`、`generated_at`

### 6.2 输出：catalog 每一行（JSONL）

| 字段 | 类型 | 说明 |
|---|---|---|
| `stem` | string | 素材 stem |
| `tags_path` | string | 相对 root 的标签路径（posix 风格） |
| `media_guess` | string \| null | 同目录同 stem 媒体相对路径 |
| `schema_version` | string \| null | 标签结构版本 |
| `generated_at` | string \| null | ISO 8601 |
| `title` | string | 标题 |
| `description` | string | 描述 |
| `keywords` | string | 关键词 |

媒体扩展名白名单（与现网一致）：  
`.mp4 .mov .mkv .webm .jpg .jpeg .png .wav .mp3`

默认输出路径：`<root>/material-tags-catalog.jsonl`（可配置覆盖）。

### 6.3 契约版本策略

- 标签文件有 `schema_version`；catalog **行格式**若破坏性变更，增加 `catalog_schema_version`（可放文件头注释行 **或** 旁路 `material-tags-catalog.meta.json`——MVP 可用 meta 接口返回，JSONL 仍保持一行一条素材，方便 LLM 逐行读）。
- **建议 MVP**：JSONL 纯记录行；元信息只走 HTTP `/v1/catalog/meta`，不塞进 JSONL 第一行，避免污染 Agent 解析。

---

## 7. API 设计（MVP）

Base：`http://<host>:<port>`（默认 `127.0.0.1:8787`，生产可绑内网 IP）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | `{ "status": "ok", "root": "...", "building": false }` |
| GET | `/v1/catalog` | `Content-Type: application/x-ndjson` 或 `application/jsonl`；流式返回文件；文件不存在 → 404 |
| GET | `/v1/catalog/meta` | `{ "path", "exists", "size", "mtime", "line_count", "last_build": { "trigger", "written", "skipped", "duration_ms", "at" } }` |
| POST | `/v1/catalog/rebuild` | 触发一次 build；返回本次统计；若正在 build 则 409 或接受排队策略（文档写死一种） |

可选头（P1）：`Authorization: Bearer <API_KEY>`；`If-None-Match` / `ETag`。

**调试**：开发默认开 FastAPI `/docs`。

---

## 8. 运行与触发语义

```text
触发源：watch（debounce） | timer | HTTP rebuild | CLI build
        │
        ▼
   [Build Lock] ──占用中→ 标记 pending，结束后再跑一轮（合并多次触发）
        │
        ▼
   scan → write tmp → rename → 更新 last_build 元数据
        │
        ▼
   GET /v1/catalog 可读新文件
```

| 配置项 | 示例 | 说明 |
|---|---|---|
| `CATALOG_ROOT` | `D:\media` / `/Volumes/media` | 必填 |
| `CATALOG_OUT` | 默认 `<root>/material-tags-catalog.jsonl` | 可选 |
| `WATCH_ENABLED` | `true` | |
| `WATCH_DEBOUNCE_SEC` | `2` | |
| `SCHEDULE_ENABLED` | `true` | |
| `SCHEDULE_INTERVAL_SEC` | `600` | 或 cron 表达式（若用 APScheduler） |
| `HOST` / `PORT` | `0.0.0.0` / `8787` | 仅内网时注意防火墙 |
| `API_KEY` | 可选 | MVP 可空=不鉴权（仅内网） |

---

## 9. 仓库结构（建仓时按此搭）

建议与现有 Codex 仓风格一致，便于 Agent 协作：

```text
material-tags-catalog-service/   # 或你的中文仓名
├── AGENTS.md                    # 仓职责、目录约定、环境、兄弟仓链接
├── README.md                    # 人读：安装、启动、API 摘要
├── requirements.txt
├── .env.example                 # 无密钥，仅变量名与示例
├── .gitignore                   # .venv cache temp output .env
├── docs/
│   ├── doc_index.md
│   ├── contracts/
│   │   └── material-tags-catalog.md   # JSONL 字段契约
│   ├── workflows/
│   │   ├── serve-catalog-service.md
│   │   └── build-catalog-once.md
│   └── faqs/
├── src/
│   └── catalog_service/
│       ├── __init__.py
│       ├── config.py            # settings
│       ├── models.py            # 记录结构 / 校验
│       ├── builder.py           # scan + build_catalog（从打标仓移植）
│       ├── media_guess.py       # 媒体猜测（可与 builder 同文件）
│       ├── scheduler.py         # timer
│       ├── watcher.py           # watchdog + debounce
│       ├── build_lock.py        # 互斥与 pending
│       ├── state.py             # last_build 内存/落盘小状态
│       └── api.py               # FastAPI routes
├── scripts/
│   └── catalog_service/
│       ├── serve.py             # 入口：起 API + watch + schedule
│       └── build.py             # 一次性 build（无 HTTP）
├── tests/
│   └── src/catalog_service/
│       ├── test_builder.py
│       ├── test_api.py
│       └── fixtures/            # 假 root 树
├── temp/                        # gitignore 内容；中间产物
├── dist/                        # gitignore；CI/本地 PyInstaller 产出
└── .venv/
```

**约束（写进 AGENTS.md）**：

- 不新增与上表冲突的顶层目录语义。
- 一仓一 `.venv`，用 `.venv/bin/python`（Windows：`.venv\Scripts\python.exe`）。
- 不依赖兄弟仓的 venv 或运行时 `sys.path` 硬编码（契约对齐靠文档/测试夹具）。

---

## 10. CLI 与启动（验收命令草案）

```bash
# 安装
uv venv && uv pip install -r requirements.txt

# 一次性
.venv/bin/python scripts/catalog_service/build.py --root /path/to/media

# 常驻（watch + schedule + HTTP）
.venv/bin/python scripts/catalog_service/serve.py
# 或读取 .env 中 CATALOG_ROOT 等
```

Windows 同等，换 python 路径；计划任务可调 `serve` 或仅 `build`。

---

## 11. 非功能需求

| 类别 | 要求 |
|---|---|
| 平台 | Windows 10+、macOS（Apple Silicon / Intel） |
| 性能 | MVP：万级标签全量重建可接受分钟级；watch debounce 避免风暴 |
| 可靠性 | 单次 build 失败不影响进程存活；坏文件 skip |
| 安全 | MVP 默认绑定可配置；内网部署；P1 API Key；不把 `.env` 入库 |
| 可观测 | 日志含 trigger、耗时、written/skipped |
| 可调试 | `fastapi` `/docs`；纯函数 builder 可单测；serve 可用 IDE 断点 |

---

## 12. 实施计划（阶段 + 任务清单）

### Phase 0 — 建仓与骨架（手动，0.5 天）

- [ ] 在 Git 托管创建空仓库（本地目录可与 `Documents/Codex/` 兄弟并列）
- [ ] 按 §9 建目录与 `.gitignore`、`.env.example`
- [ ] 写 `AGENTS.md` / `README.md` / `docs/doc_index.md`
- [ ] 写 `docs/contracts/material-tags-catalog.md`（从打标仓文档抄齐字段）
- [ ] `uv venv` + 最小 `requirements.txt`（fastapi uvicorn watchdog pydantic-settings typer …）

### Phase 1 — 核心 Builder（1–2 天）

- [ ] 移植/实现 `builder.py`（行为对齐现有 `build_catalog`）
- [ ] 原子写、skip 统计
- [ ] 单测：fixtures 假盘 → 断言 JSONL 行与字段
- [ ] CLI `build.py` 可跑通

### Phase 2 — 双触发 + 锁（1–2 天）

- [ ] `build_lock` + pending 合并
- [ ] `watcher` + debounce
- [ ] `scheduler` interval
- [ ] 集成：改 fixtures 文件能触发 rebuild（可用短 debounce 测）

### Phase 3 — FastAPI（1–2 天）

- [ ] `/health` `/v1/catalog` `/v1/catalog/meta` `/v1/catalog/rebuild`
- [ ] `serve.py` 同时挂载 API + watch + schedule
- [ ] API 测试（TestClient）
- [ ] workflow 文档：`serve-catalog-service.md`

### Phase 4 — 打磨与联调（1 天）

- [ ] 真实素材盘联调（与 File Browser 所在盘一致）
- [ ] 用 curl / Agent 拉 JSONL 做一次问答验证
- [ ] Windows + Mac 各跑通启动说明
- [ ] FAQ：端口占用、网络盘监听不可靠（靠定时兜底）、权限、UTF-8

### Phase 5 — v1.0 增强（按需）

- [ ] API Key、ETag
- [ ] launchd / Windows 服务文档
- [ ] 简单 search（可选）

**MVP 完成定义（DoD）**：在目标素材盘上 `serve` 常驻；新增一条合法 tag 后 debounce 内 JSONL 更新；远程 `GET /v1/catalog` 可读；定时仍会兜底重建；测试与 docs 登记完毕。

---

## 13. 风险与对策

| 风险 | 对策 |
|---|---|
| 网络盘 / SMB 上 watchdog 不可靠 | **定时全量必开**；watch 作加速 |
| 大盘全量慢 | debounce + pending 合并；P1 再考虑增量 |
| 与打标仓字段漂移 | 契约文档 + 双方测试夹具；破坏性变更升 version |
| 误绑公网无鉴权 | 默认文档强调内网；P1 强制 API Key 选项 |
| 与旧 `build_catalog.py` 双真相 | 文档声明：常驻以本仓为准；打标仓 CLI 仅手工兜底 |

---

## 14. 成功指标（实用向）

- Agent 获取索引：**从「File Browser 下载」变为「一次 HTTP GET」**。
- 新标签落入盘后，**无需人工**在约定时间内（如 debounce + build 完成）索引可见。
- Win/Mac 按 README **30 分钟内**可完成安装并 `GET /health` 成功。
- 核心 builder **有自动化测试**，改字段不靠手工猜。

---

## 15. 建仓最短 checklist

1. 新建空 Git 仓 + 本地目录（建议与 `多媒体资源打标` 平级）。
2. 落 §9 骨架与 `AGENTS.md`（写明：本仓是索引服务，不是打标）。
3. 复制契约字段到 `docs/contracts/`。
4. 装依赖，先实现 **builder + build CLI**，再 **serve（API+watch+timer）**。
5. 用真实素材盘验收双触发与 HTTP。
6. 在打标仓文档里加一句交叉引用：「常驻索引服务见兄弟仓 xxx」（可之后再改）。

---

## 16. 开放决策（建仓前可先定）

| 决策点 | 建议默认 |
|---|---|
| 仓库显示名 | 中文「素材标签索引服务」或英文 slug |
| 默认端口 | `8787` |
| MVP 是否强制 API Key | 否（仅内网）；文档警告 |
| JSONL 是否加文件头 | 否；元信息走 `/meta` |
| 合并代码来源 | 本仓自包含移植，不运行时依赖打标仓 |
| 测试框架 | pytest 或 unittest，二选一写进 AGENTS |
