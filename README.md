# 素材标签索引服务

贴着素材盘维护 `material-tags-catalog.jsonl`，通过 HTTP 供 Agent / 大模型远程读取。

## 运维快速上手（Windows / Mac 相同）

运维请用 **GitHub Release 便携包**，不用装 Python。两套系统步骤一样，只是启动文件名不同。

1. 打开仓库 [Releases](https://github.com/0x00pluto/material-tags-catalog-service/releases)，下载对应系统的 zip 并解压  
   - Windows：`material-tags-catalog-windows-amd64.zip`  
   - Mac：`material-tags-catalog-macos-arm64.zip`
2. 把 `.env.example` 复制为 `.env`，用记事本打开，**只改一行**：

```text
CATALOG_ROOT=你的素材盘路径
```

- Windows 示例：`CATALOG_ROOT=D:\media`
- Mac 示例：`CATALOG_ROOT=/Volumes/media`

3. 双击启动：
   - Windows：`start.bat`
   - Mac：`start.command`
4. 浏览器打开 [http://127.0.0.1:8787/health](http://127.0.0.1:8787/health)，看到 `"status":"ok"` 即成功。

常见问题：

- Mac 提示无法打开：选中文件 → 右键 → 打开
- 端口被占用：在 `.env` 里改 `PORT`（默认 `8787`）
- 不要安装 Python，也不要跑下面的开发命令

## 开发者本地运行（可选）

```bash
uv venv && uv pip install -r requirements.txt
cp .env.example .env   # 设置 CATALOG_ROOT

.venv/bin/python scripts/catalog_service/build.py --root /path/to/media
.venv/bin/python scripts/catalog_service/serve.py --root /path/to/media
```

Windows 开发将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。

## API

| 方法 | 路径 |
|---|---|
| GET | `/health` |
| GET | `/v1/catalog` |
| GET | `/v1/catalog/meta` |
| POST | `/v1/catalog/rebuild` |

默认 `http://127.0.0.1:8787`，接口文档：`/docs`。

## 更多

发版与 CI：[portable-dist-ci](docs/workflows/portable-dist-ci.md) · 开发文档索引：[doc_index](docs/doc_index.md)
