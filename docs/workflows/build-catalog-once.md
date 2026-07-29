# 一次性合并 catalog

扫描素材库根目录下的 `*.material-tags.json`，原子写出 `material-tags-catalog.jsonl`。

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

## 产物

- JSONL：字段见 [`../contracts/material-tags-catalog.md`](../contracts/material-tags-catalog.md)
- stderr：`written=` / `skipped=` / `duration_ms=`
- 有 skip 时退出码 1（整次仍写出合法行）

## 失败排查

| 现象 | 处理 |
|---|---|
| 缺少 `--root` | 必须传入素材库路径 |
| `written=0` | 检查 root 下是否有 `*.material-tags.json` |
| stderr `skip ...` | 单条缺字段或损坏；修好后重跑 |

## 测试

```bash
.venv/bin/python -m pytest tests/src/catalog_service/test_builder.py -q
```
