# 新功能开发 Loop（S1→S2→S3）

本仓索引页。角色是 **自主交付工程师**（本人实现 + 外置门禁 + PRD 回写）。

**本仓安装稿**：[`.cursor/commands/team/feature-dev.md`](../../.cursor/commands/team/feature-dev.md)

**可迁移母版**（其他工程按 SOP 安装）：Obsidian `99_Assets/Vibecoding团队/团队成员/08-自主交付工程师/`；何时装见同库 `最佳实践/功能开发闭环-自主交付工程师.md`。Agent 优先读该角色 `README.md` 与「Cursor命令模板-使用说明」。

用法：人确认 PRD 后执行 `/team:feature-dev <prd-ref> [--release R0|R1|R0,R1]`。

摘要：S0 仅人工；S1→S2→S3 由自主交付工程师自动闭环（Validator 为外置 Claude Code CLI，最多 3 轮）；**禁止本流程内发版 / 打 tag**；`base` 由 Agent 自决。发版另走 [cut-release-tag.md](./cut-release-tag.md)。
