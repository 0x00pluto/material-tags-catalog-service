# 便携分发（GitHub Actions → Release）

面向内部同事：无需安装 Python。打 tag 后 CI 在 Windows / macOS 原生机打包 zip，挂到 GitHub Release。

## 你怎么发版

1. 代码已推到 GitHub（需启用 Actions）。
2. **先写发版说明**（仓库根目录，不在 `docs/`）：

```bash
# 例如 v0.1.0 → upgrades/v0.1.0.md
# 约定见 upgrades/README.md
```

把该文件 commit 并 push 到默认分支。
3. 打版本 tag 并推送：

```bash
git tag v0.1.0
git push origin v0.1.0
```

4. 打开仓库 **Actions** → `Release portable`，等待 Win + Mac 两个 job 完成。
5. 打开 **Releases**：正文来自 `upgrades/v0.1.0.md`，附件为两个平台 zip（文件名含版本，如 `material-tags-catalog-0.1.0-windows-amd64.zip`）。

缺 `upgrades/<tag>.md` 时 Release 步骤会失败（避免空说明）。

也可在 Actions 里手动 `workflow_dispatch` 试打包（仅上传 artifact，不建 Release；只有 `v*` tag 才发 Release）。手动构建版本号为 `0.0.0+ci.<sha>`，产物名也会带上该版本字符串。


本地调试打包（非发版主路径）：

```bash
uv pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/packaging/build_portable.py --out dist
```

本地未注入 tag 时，包名会带 `0.0.0+local`。

## 版本与 tag

发版**唯一真相**是 Git tag（`v0.1.0`）。CI 打包前会把去掉 `v` 后的版本写入 [`src/catalog_service/_version.py`](../../src/catalog_service/_version.py)，再打进便携包；**同一版本**也会写进 zip / 顶层目录名。

| 场景 | `__version__` | 产物名示例 |
|---|---|---|
| 本地开发 / 未发版 | `0.0.0+local` | `material-tags-catalog-0.0.0+local-<os>-<arch>.zip` |
| `workflow_dispatch` | `0.0.0+ci.<短sha>` | 同上形态，版本段为 `0.0.0+ci.<短sha>` |
| tag `v0.1.0` | `0.1.0` | `material-tags-catalog-0.1.0-<os>-<arch>.zip` |

仓库里提交的 `_version.py` **必须一直是** `0.0.0+local`。CI（`ci.yml` 与发版流水线注入前）会校验；手改成 `0.1.0` 再 push 会失败。

查看版本：

```bash
.venv/bin/python scripts/catalog_service/serve.py --version
curl -s http://127.0.0.1:8787/health   # 含 "version" 字段
```

不要手改程序版本去「对齐」tag；发版只打对的 tag 即可。

## Release 说明

| 项 | 规则 |
|---|---|
| 路径 | 仓库根 `upgrades/vX.Y.Z.md`（与 tag 同名） |
| 用途 | GitHub Release 页面正文 |
| 缺文件 | CI 失败 |

`upgrades/` 不属于开发文档，**不**写入 `docs/doc_index.md`。

## 同事怎么用（三步）

1. 从 Release 下载对应系统的 zip（凭文件名选版本与平台），解压到任意目录。
2. 复制 `.env.example` 为 `.env`，至少改一行：`CATALOG_ROOT=...`（你的素材盘路径）。需要局域网访问时再设 `HOST=0.0.0.0`（见 [README 局域网访问](../../README.md)）。
3. 双击 `start.bat`（Windows）或 `start.command`（macOS）。

验活：本机打开 `http://127.0.0.1:8787/health`（应看到与 Release / 文件名一致的 `version`）；局域网用 `http://<服务器IP>:8787/health`。

一次性重建索引：运行包内 `build-catalog/build-catalog(.exe) --root <素材盘>`。

## 原地升级（合并解压）

发布包**永不包含**现场 `.env`（只有 `.env.example`）。推荐路径：

1. **停服务**：结束正在运行的 `catalog-service`（否则 Windows 可能因文件占用覆盖失败）。
2. **合并解压**：把新 zip 解压到**当前正在用的部署目录**（覆盖同名文件；不要先删整个目录）。也可解压出带版本号的新顶层目录后，把其中内容合并进固定路径的旧部署目录。
3. **确认配置**：包根仍有原来的 `.env`；`.env.example` 被新版本覆盖无妨。
4. **启动**：双击 `start.bat` / `start.command`。
5. **验活**：`/health` 的 `version`（或 `--version`）等于文件名中的 `{version}`。

**禁止**作为推荐升级路径：删除整个部署目录后再解压、或「清空目标目录再解压」——会导致 `.env` 丢失。升级前可选手动备份一份 `.env`。详见 [portable-upgrade-preserves-env](../faqs/portable-upgrade-preserves-env.md)。

回退：停进程 → 用旧版 zip 同样合并解压 → 确认 `.env` 仍在 → 启动。

## 包内结构

```text
material-tags-catalog-{version}-{os}-{arch}/
├── README.txt
├── .env.example          # 发布包不含 .env
├── start.bat | start.command
├── catalog-service/     # PyInstaller onedir（主程序）
└── build-catalog/       # 一次性 build
```

例：`material-tags-catalog-0.2.0-windows-amd64/`。

## 失败排查

| 现象 | 处理 |
|---|---|
| 缺少 CATALOG_ROOT | 检查包根 `.env`；`start` 会把它复制到 `catalog-service/.env` |
| 端口占用 | 改 `.env` 的 `PORT`；见 [port-already-in-use](../faqs/port-already-in-use.md) |
| macOS「无法打开」 | 选中文件 → 右键 → 打开（内部包未公证） |
| 网络盘索引滞后 | 见 [watch-unreliable-on-network-drive](../faqs/watch-unreliable-on-network-drive.md) |
| 升级后丢了 `.env` | 多半是删整目录/清空后再解压；见 [portable-upgrade-preserves-env](../faqs/portable-upgrade-preserves-env.md) |
| CI 失败 | 看 Actions 日志；确认 `requirements.txt` / 入口脚本可在该 OS 运行 |
