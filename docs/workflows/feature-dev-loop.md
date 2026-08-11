# 新功能开发 Loop（S1→S2→S3）

本仓索引页。**可迁移、独立可运行的完整 workflow 真源**在 Cursor 命令（可整文件拷到其他项目）：

[`.cursor/commands/team/feature-dev.md`](../../.cursor/commands/team/feature-dev.md)

用法：人确认 PRD 后执行 `/team:feature-dev <prd-ref> [--release R0|R1|R0,R1]`。

摘要：S0 仅人工；S1→S2→S3 由 Agent 自动闭环（Validator 为外置 Claude Code CLI，最多 3 轮）；**禁止本流程内发版 / 打 tag**；`base` 由 Agent 自决。发版另走 [cut-release-tag.md](./cut-release-tag.md)。
