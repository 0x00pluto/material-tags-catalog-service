# 契约：material-tags catalog

本仓只认约定文件格式，不依赖打标仓运行时。

## 输入：单条标签文件

- 匹配：`**/*.material-tags.json`
- 不扫描：输出 catalog 文件名（默认 `material-tags-catalog.jsonl`）
- 必填：`title`、`description`、`keywords`
- 可选：`schema_version`、`generated_at`
- 可选（schema v2 媒体元数据）：`width`、`height`、`duration_s`、`aspect_ratio`、`orientation`；缺省或坏类型写入 catalog 时为 `null`，不导致整条跳过

命名：`<stem>.material-tags.json`。

## 入索引条件

- 标签 JSON 解析与必填字段校验通过；
- **且** `guess_media_path` 命中同目录、同 stem、白名单扩展名的原媒体文件。

**无原媒体不入索引**：仅有标签、猜不到白名单媒体时，该条 **不写** JSONL 行，计入 `skipped`（`skipped_no_media`），并打 warning 日志。坏 JSON / 校验失败计入 `skipped_invalid`。CLI、watch、定时重建共用同一 `build_catalog`。

## 输出：catalog 每一行（JSONL）

每行一条 JSON（UTF-8，`ensure_ascii=False`），**无**文件头注释行。元信息走 HTTP `/v1/catalog/meta`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `stem` | string | 素材 stem |
| `tags_path` | string | 相对 root 的标签路径（posix） |
| `media_guess` | string \| null | 同目录同 stem 媒体相对路径；**正常新写入行应非空**；历史/异常快照仍可能为 null |
| `schema_version` | string \| null | 标签结构版本 |
| `generated_at` | string \| null | ISO 8601 |
| `title` | string | 标题 |
| `description` | string | 描述 |
| `keywords` | string | 关键词 |
| `width` | int \| null | 像素宽（v2 可选） |
| `height` | int \| null | 像素高（v2 可选） |
| `duration_s` | number \| null | 时长秒（v2 可选） |
| `aspect_ratio` | string \| null | 画幅比，如 `9:16`（v2 可选） |
| `orientation` | string \| null | 方向描述，如 `竖屏`（v2 可选） |

## 媒体扩展名白名单

按顺序优先：`.mp4 .mov .mkv .webm .jpg .jpeg .png .wav .mp3`

默认输出：`<root>/material-tags-catalog.jsonl`（可配置覆盖）。

写入策略：先写临时文件再 `os.replace`，避免读到半截。

`BuildResult` / `last_build`（meta）：`skipped` = `skipped_no_media` + `skipped_invalid`；HTTP search / 全量读 **不**二次过滤历史 null 行，靠下次成功 rebuild 清掉。

## HTTP 检索（只读）

`GET /v1/catalog/search` 扫描当前 catalog JSONL，按关键词返回排序后的行子集。

- **不**新增、不修改 JSONL 行字段；`items[]` 与上表一致。
- 查询参数、匹配规则（AND 子串、casefold、加权排序）、Agent 用法见 [workflows/serve-catalog-service.md](../workflows/serve-catalog-service.md)。
