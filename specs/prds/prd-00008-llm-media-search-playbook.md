---
name: prd-00008-llm-media-search-playbook
sequence: 8
description: 本仓落地一份大模型可读的 HTTP 媒体检索 playbook：curl search、自拼 File Browser 下载链、固定回复模板；不依赖技能脚本
status: implemented
created: 2026-08-11T06:22:53Z
last_accepted_at: 2026-08-11T06:39:01Z
accepted_commit: 8fa4952
accepted_branch: main
accepted_scope: R0
---

# PRD: LLM 媒体检索 Playbook（HTTP 一二三）

| 项 | 内容 |
|---|---|
| 状态 | 工程：`implemented`（R0 已 accepted；R1 HTTP 渲染已落地，待 `/team:prd-accept` 重验，见文末「工程验收状态」） |
| 范围 | **R0 文档** + **R1 服务侧**：playbook 模板；`GET /v1/docs/llm-media-search-playbook` 按请求注入 `api_base`、可选 `FILE_BROWSER_BASE`→`file_base`；不改 search 语义、不拷贝外部技能脚本 |
| 关联文档 | `docs/workflows/llm-media-search-playbook.md`（本 PRD 主交付）、`docs/workflows/serve-catalog-service.md`、`docs/contracts/material-tags-catalog.md`、`docs/doc_index.md` |
| 父/相关 | `prd-00002`（关键词 search）、`prd-00006`（`path_prefix`）；外部技能仅作历史参考，**非**运行时依赖；本仓 playbook **独立**于互远技能包 |

## 1. 背景与问题

### 1.1 现状

- 本仓已提供 `GET /v1/catalog/search`（关键词 AND + 可选 `path_prefix`），契约与 serve workflow 已写清参数与匹配规则。
- 企业侧另有技能包 `huyuan-ai-media-resource-finder-master`：封装配置、`search.mjs`、下载 URL 拼接与对用户回复模板。
- 未安装该技能的 Agent / 同事只能读 serve 运维文档，缺少一份**自包含、步骤化、面向「回复用户」**的手册（含 `download_url` 公式与强制展示格式）。

### 1.2 要解决的问题

1. **去技能依赖**：任意能读本仓文档、能访问内网的大模型，按一二三即可完成「搜 → 拼链 → 按模板回复」。
2. **补齐展示契约**：serve 文档止于 API；playbook 须写死 File Browser URL 公式与对用户 Markdown 硬约束（全文 description、元数据缺省「未知」、禁止编造链接等）。
3. **分流文档角色**：运维继续读 serve workflow；找素材 Agent 读 playbook。

### 1.3 价值假设

技能变为可选快捷封装；本仓文档成为找素材行为的单一事实源入口，降低「没装技能就不会搜」的协作成本。

## 2. 目标与非目标

### 2.1 目标（MVP / Release 0）

- 新增 [`docs/workflows/llm-media-search-playbook.md`](../../docs/workflows/llm-media-search-playbook.md)：
  - 何时用 / 不用（边界表）
  - 前置 `api_base` / `file_base` 默认值
  - 推荐顺序：先 `path_prefix` → 再短关键词 `q` → `curl --get`
  - **硬编码** `download_url` 公式（分段 `encodeURIComponent`，不依赖 Node）
  - 从 catalog 行字段推导画幅 / 时长 / 比例展示（null →「未知」）
  - 对用户回复模板与硬约束
  - 改写 / 翻页建议；正例 / 反例（curl 版）
- 登记进 [`docs/doc_index.md`](../../docs/doc_index.md)。
- 在 [`docs/workflows/serve-catalog-service.md`](../../docs/workflows/serve-catalog-service.md) 的 Agent 找素材段交叉链接到本 playbook。

### 2.1.1 目标（Release 1）

- `GET /v1/docs/llm-media-search-playbook`：返回 `text/markdown`；用**本次请求** `Request.base_url` 注入 `{{api_base}}`。
- 可选 ENV `FILE_BROWSER_BASE` → 注入 `{{file_base}}`；未设则标明未配置、不要求拼下载链。
- 仓库 md 为占位符模板；HTTP 响应为渲染结果。不与外部技能包 / `~/.huyuan-ai` 耦合。
- 便携包旁挂 playbook 文件；补充 pytest。

### 2.2 非目标

- 安装 / 分发 / 维护外部「媒体查找」技能包或将其脚本拷入本仓。
- Agent 调用 `POST /v1/catalog/rebuild`（运维侧；playbook 明确禁止自行 rebuild）。
- 改动 `GET /v1/catalog/search` 语义、响应 schema、或新增 `download_url` / `*_display` API 字段。
- 向量检索 / RAG / 公网图库 / CDN 上传 / 本地磁盘递归扫文件。
- 写入 `upgrades/`（除非另开发版任务）。
- 反向代理 `X-Forwarded-*` 适配（当前按内网直连；网关场景后续另议）。

## 3. 术语

| 术语 | 含义 |
|---|---|
| playbook | 本仓面向大模型的可执行 Markdown：读完即可 curl + 拼链 + 回复 |
| `api_base` | Catalog HTTP 根，无尾斜杠；HTTP 拉取时由本实例请求地址注入，非写死 IP |
| `file_base` | File Browser 下载前缀，无尾斜杠；来自可选 `FILE_BROWSER_BASE`，未配置则不拼链 |
| `download_url` | `{file_base}/{分段编码后的 media_guess}`；由调用方自拼，API 不返回 |
| 正式索引源 | 磁盘 `material-tags-catalog.jsonl`；search 只读；行字段见契约 |

## 4. 已拍板规则 / 取舍

| 主题 | 决议 | 说明 |
|---|---|---|
| 落点 | 本仓 `docs/workflows/` | 登记 `doc_index`；不新建仓库顶层目录 |
| 执行路径 | **纯 HTTP** | `curl` + search + 自拼 URL；不写技能脚本主路径 |
| search 语义 | 与现网一致 | 引用 prd-00002 / 00006；playbook 不另造匹配规则 |
| 元数据展示 | 调用方格式化 | API 无 `*_display`；playbook 规定 null→「未知」、`duration_s`→`{n}s` |
| rebuild | **Agent 不调用** | 404 / 索引缺失交运维；与技能边界一致 |
| 技能关系 | 行为参考，非依赖 | 可与技能并存；本仓 playbook 为未装技能时的权威步骤 |

## 5. 用户故事

1. 作为内网 Agent，我读完 playbook 后，用 curl 按项目路径 + 关键词搜到条目，并给用户可点击的下载链接与完整描述。
2. 作为未装技能的同事，我把 playbook 路径丢给任意大模型，即可复现找素材流程，无需安装 Node 技能包。
3. 作为运维，我仍用 serve workflow 管服务；Agent 手册与运维文档通过交叉链接分流，不互相淹没。

## 6. 验收标准（Release 0）

| ID | 标准 | 验证方式 |
|---|---|---|
| R0-01 | 存在 `docs/workflows/llm-media-search-playbook.md` | 路径存在 |
| R0-02 | 含：边界表、api_base/file_base、curl 示例（含 path_prefix）、download_url 公式、回复模板与硬约束、改写/翻页、正反例 | 人工通读清单 |
| R0-03 | `docs/doc_index.md` 有一行指向该 playbook | 索引表 |
| R0-04 | `serve-catalog-service.md` Agent 段链到该 playbook | 链接可点 |
| R0-05 | 与契约 / serve 的 search 参数无矛盾；不要求 Agent 调 rebuild | 对照阅读 |
| R0-06 | 用一份样例 search JSON（或真实 curl）可按模板写出合规 Markdown 回复 | 人工演练 |

## 6.1 验收标准（Release 1）

| ID | 标准 | 验证方式 |
|---|---|---|
| R1-01 | `GET /v1/docs/llm-media-search-playbook` 返回 200 + `text/markdown` | curl |
| R1-02 | 正文 `api_base` / curl 目标与请求 host:port 一致（如 PORT=11777） | curl 对照 |
| R1-03 | 设 `FILE_BROWSER_BASE` 时注入该值；未设时标明未配置 | 环境对照 |
| R1-04 | 正文不写死互远默认盘前缀 / 内网 IP；主路径仍为纯 HTTP；允许文末「可选装技能」指针（含安装命令） | 通读 / rg（禁 `huanyuan-share`、禁写死 `192.168.0.8`） |
| R1-05 | OpenAPI 登记该路径；search 回归可用 | openapi + curl |

## 7. 依赖与风险

| 项 | 说明 | 缓解 |
|---|---|---|
| 内网地址变更 | `api_base` 随部署 HOST/PORT 变化 | HTTP playbook 按请求注入；勿写死 IP |
| File Browser 权限 | URL 正确仍可能 404 / 需登录 | playbook 注明仅拼链、不代登录；依赖 `FILE_BROWSER_BASE` |
| 与外部技能双源 | 技能与 playbook 日后漂移 | 本仓 playbook 为本服务权威步骤；不耦合技能仓 |

## 8. 修订记录

| 日期 | 说明 |
|---|---|
| 2026-08-11 | 初稿：纯文档 PRD；HTTP playbook；不依赖技能脚本 |
| 2026-08-11 | R1：HTTP 渲染 api_base / FILE_BROWSER_BASE；去技能耦合；修正非目标（允许本仓 src 支撑文档路由） |

## 9. 工程验收状态

> 由 `/team:prd-accept` 维护；勿手工编造「通过」。最后更新：2026-08-11T06:39:01Z，main@8fa4952，范围：R0（正式 accepted）。**R1 已实现并经接口验收，状态改为 `implemented`，请重新跑 `/team:prd-accept --release R0,R1` 回写本节。**

### 总览

| 项 | 内容 |
|---|---|
| 工程状态 | `accepted` |
| 验收判定 | 通过（R0 全通过；本 PRD 无 R1，标范围外） |
| 最近验收 | 2026-08-11T06:39:01Z，main@8fa4952，范围 R0,R1 |
| 代码提交 | 交付物在工作区：`docs/workflows/llm-media-search-playbook.md`（未跟踪）及 doc_index / serve / 契约交叉链修改；HEAD `8fa4952` 尚未含上述文档 |
| 摘要 | ① playbook 已落地且含 R0 必备章节；② `doc_index` 已登记；③ serve Agent 段已交叉链接；④ 禁 rebuild、search 语义与契约/serve 一致；⑤ §8.1 样例 JSON→合规回复可演练 |

### Release 交付

| Release | 状态 | 说明 |
|---|---|---|
| R0 | 通过 | 纯文档 playbook + 索引 + serve 交叉链；R0-01～R0-06 均有路径证据 |
| R1 | 范围外 | 本 PRD 未定义 Release 1 |

### 功能验收清单（Agent 优先读此表）

| ID | 能力摘要 | Release | 状态 | 证据 |
|---|---|---|---|---|
| R0-01 | 存在 `docs/workflows/llm-media-search-playbook.md` | R0 | 通过 | 路径存在（工作区未跟踪文件） |
| R0-02 | 边界表、api/file_base、curl+path_prefix、download_url 公式、模板/硬约束、改写翻页、正反例 | R0 | 通过 | playbook §1–§10；含 encodeURIComponent 伪代码与硬约束 |
| R0-03 | `docs/doc_index.md` 登记一行 | R0 | 通过 | `docs/doc_index.md` L8 |
| R0-04 | serve Agent 段链到 playbook | R0 | 通过 | `serve-catalog-service.md` L96 |
| R0-05 | 与契约/serve search 无矛盾；禁止 Agent rebuild | R0 | 通过 | playbook L18/L168 禁 rebuild；path_prefix OR/20/`..`→400 与 serve 一致；契约 L65 链回 playbook |
| R0-06 | 样例 search JSON → 合规 Markdown | R0 | 通过 | playbook §8.1；分段 `quote` 与样例下载 URL 一致 |
| US-1 | Agent 读 playbook 可 curl + 拼链 + 完整描述回复 | R0 | 通过 | §3–§6 + §8.1 |
| US-2 | 未装技能同事可复现流程 | R0 | 通过 | 纯 HTTP；不依赖技能/`~/.huyuan-ai` |
| US-3 | 运维与 Agent 文档分流 | R0 | 通过 | serve ↔ playbook 交叉链 |

### 未完成与遗留

- 交付文档与交叉链仍在 **工作区未 commit**（含未跟踪 playbook）；合入后建议更新 `accepted_commit`。
- §非目标（技能包、改 search API、`src/`/pytest、upgrades）未纳入本验收。

### 质量检查

| 检查项 | 状态 |
|---|---|
| `.venv/bin/python -m pytest -q` | 通过（72 passed，1 warning；本 PRD 非目标为不新增单测，回归绿） |
| （无） | — |
| 文档与 OpenAPI 同步 | 通过（本 PRD 不改 API；playbook 声明无 `download_url`/`*_display` 字段，与契约一致） |

---
统计：通过 9 / 部分 0 / 未实现 0 / 范围外 1（R1）
