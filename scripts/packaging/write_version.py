#!/usr/bin/env python3
"""写入 src/catalog_service/_version.py（CI 从 Git tag 注入）。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "src" / "catalog_service" / "_version.py"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def write_version(version: str) -> None:
    text = (
        '"""程序版本号。\n'
        "\n"
        "发版唯一真相为 Git tag（vX.Y.Z）；CI 在打包前覆盖本文件。\n"
        "本地开发默认为 0.0.0+local。\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        f'__version__ = "{version}"\n'
    )
    VERSION_FILE.write_text(text, encoding="utf-8")
    print(f"wrote {VERSION_FILE} __version__={version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write package version file")
    parser.add_argument("--version", required=True, help="如 0.1.0 或 0.0.0+ci.abc1234")
    parser.add_argument(
        "--require-semver",
        action="store_true",
        help="要求严格 MAJOR.MINOR.PATCH（发版 tag 用）",
    )
    args = parser.parse_args()
    version = args.version.strip()
    if version.startswith("v"):
        version = version[1:]
    if args.require_semver and not SEMVER_RE.match(version):
        print(
            f"版本不符合 SemVer X.Y.Z: {version!r}（tag 请用 v0.1.0 这种形式）",
            file=sys.stderr,
        )
        return 2
    write_version(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
