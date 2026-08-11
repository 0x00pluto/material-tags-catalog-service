# 文档索引

| 路径 | 摘要 |
|---|---|
| [contracts/material-tags-catalog.md](./contracts/material-tags-catalog.md) | JSONL / 标签契约与媒体白名单（含 `.webp`）；v2 可选透传 width/height/duration_s/aspect_ratio/orientation；`.material_index` 可父目录猜媒体；`SCAN_EXCLUDE_DIR_NAMES` 任意深度排除；合法 orphan 默认 purge；HTTP search 只读现有行，可选 `path_prefix` 仅过滤 `tags_path` |
| [workflows/build-catalog-once.md](./workflows/build-catalog-once.md) | 一次性 CLI 合并 catalog（与常驻共用写侧过滤） |
| [workflows/serve-catalog-service.md](./workflows/serve-catalog-service.md) | 常驻：先 listen、后台 startup；watch 启动静默窗 + 定时 + FastAPI；search 支持可选 `path_prefix`；`GET /v1/docs/llm-media-search-playbook`（按请求注入 api_base）；可选 `FILE_BROWSER_BASE`；开发一键 `dev-serve.sh` / `dev-test.sh` |
| [workflows/llm-media-search-playbook.md](./workflows/llm-media-search-playbook.md) | 本服务 Agent 检索手册：curl search、可选拼 download_url、回复模板；HTTP 拉取时注入本实例 api_base / FILE_BROWSER_BASE；可选装 `huyuan-ai-media-resource-finder-master`；不调 rebuild |
| [workflows/portable-dist-ci.md](./workflows/portable-dist-ci.md) | Win/Mac 便携包：CI 打 tag 发 Release、一键升级脚本、同事三步用法 |
| [workflows/cut-release-tag.md](./workflows/cut-release-tag.md) | 本地写 upgrades + 打 tag（SemVer；major 须人指定）；用户推送远程 |
| [workflows/feature-dev-loop.md](./workflows/feature-dev-loop.md) | 新功能 S1→S2→S3 索引；完整可迁移规则见 `.cursor/commands/team/feature-dev.md`（禁 tag/发版；Claude Code Validator；最多 3 轮） |
| [faqs/watch-unreliable-on-network-drive.md](./faqs/watch-unreliable-on-network-drive.md) | 网络盘监听不可靠时靠定时兜底 |
| [faqs/port-already-in-use.md](./faqs/port-already-in-use.md) | 端口占用排查 |
| [faqs/windows-lan-access-and-console-garbled.md](./faqs/windows-lan-access-and-console-garbled.md) | Windows：局域网 HOST / 防火墙；CMD 快速编辑假死（start.bat + 进程内双关；看 `quick-edit disabled` 日志）；ANSI「乱码」 |
| [faqs/macos-gatekeeper-portable.md](./faqs/macos-gatekeeper-portable.md) | macOS 便携包 Gatekeeper「无法打开」 |
| [faqs/portable-upgrade-preserves-env.md](./faqs/portable-upgrade-preserves-env.md) | 便携包合并解压 / 一键升级会否丢掉 `.env` |
