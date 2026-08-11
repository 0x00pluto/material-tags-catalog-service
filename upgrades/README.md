# 发版说明（upgrades）

面向 GitHub Release 正文，**不是**开发文档（开发文档在 `docs/`）。

每个 Git tag 对应一份 Markdown，文件名与 tag **完全一致**（含 `v` 前缀）。

| tag | 文件 |
|---|---|
| `v0.1.0` | [`v0.1.0.md`](./v0.1.0.md) |
| `v0.2.0` | [`v0.2.0.md`](./v0.2.0.md) |
| `v0.3.0` | [`v0.3.0.md`](./v0.3.0.md) |
| `v0.4.0` | [`v0.4.0.md`](./v0.4.0.md) |
| `v0.4.1` | [`v0.4.1.md`](./v0.4.1.md) |
| `v0.5.0` | [`v0.5.0.md`](./v0.5.0.md) |
| `v0.6.0` | [`v0.6.0.md`](./v0.6.0.md) |
| `v0.6.1` | [`v0.6.1.md`](./v0.6.1.md) |
| `v0.7.0` | [`v0.7.0.md`](./v0.7.0.md) |
| `v0.7.1` | [`v0.7.1.md`](./v0.7.1.md) |
| `v0.8.0` | [`v0.8.0.md`](./v0.8.0.md) |

CI 创建 Release 时把该文件全文作为正文；**缺少对应文件则发版失败**。

发版前：先写好 `upgrades/vX.Y.Z.md` 并提交，再打 tag 推送。

Agent / 协作流程（查变更 → 写本目录 → 本地 tag → 人推送）：见 [`docs/workflows/cut-release-tag.md`](../docs/workflows/cut-release-tag.md)。版号按 SemVer；**升 major 必须人工显式指定**。
