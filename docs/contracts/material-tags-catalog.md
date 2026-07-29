# 契约：material-tags catalog

本仓只认约定文件格式，不依赖打标仓运行时。

## 输入：单条标签文件

- 匹配：`**/*.material-tags.json`
- 不扫描：输出 catalog 文件名（默认 `material-tags-catalog.jsonl`）
- 必填：`title`、`description`、`keywords`
- 可选：`schema_version`、`generated_at`

命名：`<stem>.material-tags.json`。

## 输出：catalog 每一行（JSONL）

每行一条 JSON（UTF-8，`ensure_ascii=False`），**无**文件头注释行。元信息走 HTTP `/v1/catalog/meta`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `stem` | string | 素材 stem |
| `tags_path` | string | 相对 root 的标签路径（posix） |
| `media_guess` | string \| null | 同目录同 stem 媒体相对路径 |
| `schema_version` | string \| null | 标签结构版本 |
| `generated_at` | string \| null | ISO 8601 |
| `title` | string | 标题 |
| `description` | string | 描述 |
| `keywords` | string | 关键词 |

## 媒体扩展名白名单

按顺序优先：`.mp4 .mov .mkv .webm .jpg .jpeg .png .wav .mp3`

默认输出：`<root>/material-tags-catalog.jsonl`（可配置覆盖）。

写入策略：先写临时文件再 `os.replace`，避免读到半截。
