#!/usr/bin/env python3
"""断言仓库内 _version.py 仍为 0.0.0+local（禁止手改发版号入库）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "src" / "catalog_service" / "_version.py"
EXPECTED = "0.0.0+local"
ASSIGN_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$', re.M)


def main() -> int:
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = ASSIGN_RE.search(text)
    if match is None:
        print(f"无法解析 {VERSION_FILE} 中的 __version__", file=sys.stderr)
        return 1
    actual = match.group(1)
    if actual != EXPECTED:
        print(
            f"仓库内版本必须是 {EXPECTED!r}，当前为 {actual!r}。\n"
            f"发版号由 Git tag + CI 注入，请勿手改 {VERSION_FILE.relative_to(ROOT)}。",
            file=sys.stderr,
        )
        return 1
    print(f"ok: {VERSION_FILE.relative_to(ROOT)} == {EXPECTED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
