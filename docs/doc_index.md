# 文档索引

| 路径 | 摘要 |
|---|---|
| [contracts/material-tags-catalog.md](./contracts/material-tags-catalog.md) | JSONL / 标签契约与媒体白名单；v2 可选透传 width/height/duration_s/aspect_ratio/orientation；`.material_index` 可父目录猜媒体；无原媒体不入索引；HTTP search 只读现有行 |
| [workflows/build-catalog-once.md](./workflows/build-catalog-once.md) | 一次性 CLI 合并 catalog（与常驻共用写侧过滤） |
| [workflows/serve-catalog-service.md](./workflows/serve-catalog-service.md) | 常驻：watch + 定时 + FastAPI；开发一键 `dev-serve.sh` / `dev-test.sh` |
| [workflows/portable-dist-ci.md](./workflows/portable-dist-ci.md) | Win/Mac 便携包：CI 打 tag 发 Release、一键升级脚本、同事三步用法 |
| [workflows/cut-release-tag.md](./workflows/cut-release-tag.md) | 本地写 upgrades + 打 tag（SemVer；major 须人指定）；用户推送远程 |
| [faqs/watch-unreliable-on-network-drive.md](./faqs/watch-unreliable-on-network-drive.md) | 网络盘监听不可靠时靠定时兜底 |
| [faqs/port-already-in-use.md](./faqs/port-already-in-use.md) | 端口占用排查 |
| [faqs/windows-lan-access-and-console-garbled.md](./faqs/windows-lan-access-and-console-garbled.md) | Windows：局域网 HOST / 防火墙；CMD 快速编辑假死；ANSI「乱码」 |
| [faqs/macos-gatekeeper-portable.md](./faqs/macos-gatekeeper-portable.md) | macOS 便携包 Gatekeeper「无法打开」 |
| [faqs/portable-upgrade-preserves-env.md](./faqs/portable-upgrade-preserves-env.md) | 便携包合并解压 / 一键升级会否丢掉 `.env` |
