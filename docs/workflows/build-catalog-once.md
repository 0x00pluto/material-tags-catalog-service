# 一次性合并 catalog

扫描素材库根目录下的 `*.material-tags.json`，原子写出 `material-tags-catalog.jsonl`。

与常驻服务的 watch / 定时 / HTTP rebuild **共用** `build_catalog`：排除目录不扫；无白名单原媒体的标签不入索引，默认物理清理合法 orphan（详见契约「入索引条件」）。CLI 会读 `.env` 中的 `SCAN_EXCLUDE_DIR_NAMES` / `PURGE_ORPHAN_TAGS`（`--root` 覆盖 `CATALOG_ROOT`）。

## 入口

```bash
cd <本工作区>
.venv/bin/python scripts/catalog_service/build.py --help
```

```bash
.venv/bin/python scripts/catalog_service/build.py --root /path/to/media-library
```

指定输出：

```bash
.venv/bin/python scripts/catalog_service/build.py \
  --root /path/to/media-library \
  --out /path/to/media-library/material-tags-catalog.jsonl
```

Windows：`.venv\Scripts\python.exe scripts\catalog_service\build.py --root D:\media`

## 参数

| 参数 | 说明 |
|---|---|
| `--root` | **必填**。素材库根目录 |
| `--out` | 输出路径，默认 `<root>/material-tags-catalog.jsonl` |

环境变量（见 `.env.example`）：`SCAN_EXCLUDE_DIR_NAMES`、`PURGE_ORPHAN_TAGS`（默认 true）。

## 产物

- JSONL：字段见 [`../contracts/material-tags-catalog.md`](../contracts/material-tags-catalog.md)；正常行带非空 `media_guess`
- stderr：`written=` / `skipped=` / `skipped_no_media=` / `skipped_invalid=` / `skipped_excluded=` / `purged=` / `duration_ms=`
- 有 skip 时退出码 1（整次仍写出合法行；`skipped` 不含 excluded）

## 失败排查

| 现象 | 处理 |
|---|---|
| 缺少 `--root` | 必须传入素材库路径 |
| `written=0` | 检查 root 下是否有 `*.material-tags.json`，且同目录（或 `.material_index` 的直接父目录）有白名单媒体；是否被排除目录跳过 |
| stderr `purged orphan …` | 合法 orphan 已删旁车；补媒体后需上游重打标 |
| stderr `skip …: no media`（purge 关） | 仅有标签无原媒体；补媒体或手动清理后重跑 |
| stderr `purge failed …` | unlink 失败（权限/只读盘等）；其余条目仍写入 |
| stderr `skip …`（其它） | 单条缺字段或损坏；修好后重跑（坏 JSON **不**自动删除） |

## 测试

```bash
.venv/bin/python -m pytest tests/src/catalog_service/test_builder.py -q
```
