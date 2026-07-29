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
5. 打开 **Releases**：正文来自 `upgrades/v0.1.0.md`，附件为两个平台 zip。

缺 `upgrades/<tag>.md` 时 Release 步骤会失败（避免空说明）。

也可在 Actions 里手动 `workflow_dispatch` 试打包（仅上传 artifact，不建 Release；只有 `v*` tag 才发 Release）。手动构建版本号为 `0.0.0+ci.<sha>`。


本地调试打包（非发版主路径）：

```bash
uv pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/packaging/build_portable.py --out dist
```

## 版本与 tag

发版**唯一真相**是 Git tag（`v0.1.0`）。CI 打包前会把去掉 `v` 后的版本写入 [`src/catalog_service/_version.py`](../../src/catalog_service/_version.py)，再打进便携包。

| 场景 | `__version__` |
|---|---|
| 本地开发 / 未发版 | `0.0.0+local` |
| `workflow_dispatch` | `0.0.0+ci.<短sha>` |
| tag `v0.1.0` | `0.1.0`（与 Release / tag 一致；仅打进便携包） |

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

1. 从 Release 下载对应系统的 zip，解压到任意目录。
2. 复制 `.env.example` 为 `.env`，只改一行：`CATALOG_ROOT=...`（你的素材盘路径）。
3. 双击 `start.bat`（Windows）或 `start.command`（macOS）。

验活：浏览器打开 `http://127.0.0.1:8787/health`（应看到与 Release 一致的 `version`）。

一次性重建索引：运行包内 `build-catalog/build-catalog(.exe) --root <素材盘>`。

## 包内结构

```text
material-tags-catalog-<os>-<arch>/
├── README.txt
├── .env.example
├── start.bat | start.command
├── catalog-service/     # PyInstaller onedir（主程序）
└── build-catalog/       # 一次性 build
```

## 失败排查

| 现象 | 处理 |
|---|---|
| 缺少 CATALOG_ROOT | 检查包根 `.env`；`start` 会把它复制到 `catalog-service/.env` |
| 端口占用 | 改 `.env` 的 `PORT`；见 [port-already-in-use](../faqs/port-already-in-use.md) |
| macOS「无法打开」 | 选中文件 → 右键 → 打开（内部包未公证） |
| 网络盘索引滞后 | 见 [watch-unreliable-on-network-drive](../faqs/watch-unreliable-on-network-drive.md) |
| CI 失败 | 看 Actions 日志；确认 `requirements.txt` / 入口脚本可在该 OS 运行 |
