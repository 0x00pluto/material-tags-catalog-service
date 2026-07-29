# 打发版 tag（本地说明 + tag；用户推送）

可复跑：从上一 Git tag 到当前 HEAD 汇总变更 → 写 `upgrades/` 发版页 → 本地提交并打 tag → **由人推送远程**。推送后的 CI / 便携包流程见 [portable-dist-ci.md](./portable-dist-ci.md)。

## 分工

| 角色 | 职责 |
|---|---|
| Agent | 查上一 tag..HEAD 变更；按 SemVer 定版号（major 除外）；写 `upgrades/vX.Y.Z.md`；更新 `upgrades/README.md` 索引；本地 `git commit` + `git tag`；**只给出**推送命令 |
| 人 | major（及跳号 / 覆盖版号）时**显式指定**；自行 `git push`（Agent **禁止** push） |

## 版号规则（SemVer · 铁律）

相对上一 tag `vMAJOR.MINOR.PATCH`：

| 变更类型 | 怎么升 | 谁决定 |
|---|---|---|
| 小补丁 / 修复 / 与发版无关的小改 | `PATCH +1`（如 `0.3.1` → `0.3.2`） | Agent 按 SemVer 自动取下一号 |
| 功能变更 / 向后兼容的新能力 | `MINOR +1`，`PATCH` 归零（如 `0.3.1` → `0.4.0`） | Agent 按 SemVer 自动取下一号 |
| 不兼容 / 重大跃迁（如 `1.0.0` → `2.0.0`） | `MAJOR +1`，`MINOR` / `PATCH` 归零 | **必须人显式指定**；Agent **禁止**自行升 major |

细则：

- Agent 根据「上一 tag..HEAD」判定 patch 或 minor，直接采用算出的 `$TAG`。
- 若可能涉及 **breaking / major**：Agent **停住**，说明理由并请人给出目标 major（如 `v2.0.0`）；未得到明确 major 目标前，不得打 major tag。
- 人可随时覆盖：显式说出目标 tag（含 patch / minor）时，以指定为准。
- 跳号（如 `0.3.0` → `0.5.0`）须人显式指定；默认不跳号。
- 勿手改 [`src/catalog_service/_version.py`](../../src/catalog_service/_version.py)；仓库内须保持 `0.0.0+local`，发版真相是 Git tag（CI 注入）。

## 步骤

### 0. 前置

- 功能改动已提交到默认分支（或即将随本流程一并提交的仅限 upgrades 相关文件）。
- 工作区干净，或仅剩即将写入的 `upgrades/` 文件。
- 确认 Actions / 远程发版约定见 [portable-dist-ci.md](./portable-dist-ci.md)；本流程只负责本地说明 + tag。

### 1. 查上一 tag 与变更

```bash
PREV=$(git tag -l 'v*' --sort=-v:refname | head -1)
echo "prev=$PREV"
git log "${PREV}..HEAD" --oneline
git diff "${PREV}..HEAD" --stat
```

把用户可见变更整理成「相对 `$PREV`」的要点（供发版页正文）。

### 2. 定版号 `$TAG`

1. 解析 `$PREV` → `MAJOR.MINOR.PATCH`。
2. 按上表：patch → `vMAJOR.MINOR.(PATCH+1)`；minor → `vMAJOR.(MINOR+1).0`。
3. 若需 major、跳号或人已指定覆盖版号 → **等人口头确认** `$TAG`（须 `vX.Y.Z`）。
4. 确认本地尚无同名 tag：`git rev-parse "$TAG" 2>/dev/null` 应失败。

### 3. 写发版页并登记索引

- 新建 `upgrades/$TAG.md`（文件名与 tag **完全一致**，含 `v`）。
- 在 [`upgrades/README.md`](../../upgrades/README.md) 表格增加一行。

体例对齐既有页：标题 `# $TAG` → 相对上一 tag 一句话 → `## 变更` → `## 升级注意`。

缺 `upgrades/<tag>.md` 时 CI 创建 Release **失败**。

### 4. Agent 本地提交并打 tag

```bash
git add "upgrades/${TAG}.md" upgrades/README.md
git commit -m "$(cat <<EOF
docs(upgrades): 增加 ${TAG} 发版说明

EOF
)"
git tag "$TAG"
```

仅当还有未提交的功能代码且人要求一并入库时，才额外 `git add` 那些路径；默认本步只提交 upgrades。

### 5. 人推送远程（Agent 只输出命令，不执行）

```bash
git push origin main
git push origin "$TAG"
```

分支名若非 `main`，换成当前默认分支。

### 6. 之后

按 [portable-dist-ci.md](./portable-dist-ci.md)：Actions → `Release portable` → 打开 Releases 核对正文与 zip → 升级后 `/health` 的 `version` 与 tag 去掉 `v` 一致。

## 发版页模板

```markdown
# vX.Y.Z

相对 `vA.B.C`：一句话说明本版相对上一 tag 的主题。

## 变更

- …

## 升级注意

- 可用包内 `upgrade.bat` / `upgrade.command`（或 `-y`）一键升级；或停服后合并解压本版 zip（勿删整目录，保留 `.env`）
- 升级后手动启动，打开 `/health` 确认 `version` 为 `X.Y.Z`
```

## 验收清单

- [ ] `$TAG` 符合 SemVer 规则（major 已经人指定，或未升 major）
- [ ] 存在 `upgrades/$TAG.md`，且已写入 `upgrades/README.md`
- [ ] 本地存在 lightweight tag `$TAG`，指向含发版说明的 commit
- [ ] Agent 已给出 `git push origin <branch>` 与 `git push origin $TAG`，且**未**代推
