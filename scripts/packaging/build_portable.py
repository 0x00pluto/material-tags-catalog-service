#!/usr/bin/env python3
"""构建便携分发包（PyInstaller onedir → zip）。CI 与本地调试共用。"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).resolve().parent / "assets"


def _platform_slug() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        os_name = "macos"
    elif system == "windows":
        os_name = "windows"
    else:
        os_name = system
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine
    return os_name, arch


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


def _pyinstaller(name: str, entry: Path, dist_dir: Path, work_dir: Path) -> Path:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        name,
        "--paths",
        str(ROOT),
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        str(entry),
    ]
    _run(cmd)
    built = dist_dir / name
    if not built.is_dir():
        raise RuntimeError(f"PyInstaller 未产出目录: {built}")
    return built


def _write_start_scripts(stage: Path, os_name: str) -> None:
    """包根维护 .env；启动时复制到 exe 旁（frozen 从 exe 目录读）。"""
    if os_name == "windows":
        (stage / "start.bat").write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            "cd /d \"%~dp0\"\r\n"
            "\r\n"
            "if not exist \".env\" (\r\n"
            "  if exist \".env.example\" (\r\n"
            "    copy /Y \".env.example\" \".env\" >nul\r\n"
            "    echo 已从 .env.example 复制出 .env，请先编辑 CATALOG_ROOT 后再启动。\r\n"
            "    notepad \".env\"\r\n"
            "    exit /b 1\r\n"
            "  )\r\n"
            "  echo 缺少 .env，请复制 .env.example 为 .env 并设置 CATALOG_ROOT。\r\n"
            "  exit /b 1\r\n"
            ")\r\n"
            "copy /Y \".env\" \"catalog-service\\.env\" >nul\r\n"
            "echo 启动 catalog-service ...\r\n"
            "\"%~dp0catalog-service\\catalog-service.exe\"\r\n"
            "endlocal\r\n",
            encoding="utf-8",
        )
        return

    start = stage / "start.command"
    start.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "cd \"$(dirname \"$0\")\"\n"
        "\n"
        "if [[ ! -f .env ]]; then\n"
        "  if [[ -f .env.example ]]; then\n"
        "    cp .env.example .env\n"
        "    echo \"已从 .env.example 复制出 .env，请先编辑 CATALOG_ROOT 后再启动。\"\n"
        "    ${EDITOR:-open} .env || true\n"
        "    exit 1\n"
        "  fi\n"
        "  echo \"缺少 .env，请复制 .env.example 为 .env 并设置 CATALOG_ROOT。\"\n"
        "  exit 1\n"
        "fi\n"
        "\n"
        "cp -f .env ./catalog-service/.env\n"
        "chmod +x ./catalog-service/catalog-service 2>/dev/null || true\n"
        "echo \"启动 catalog-service ...\"\n"
        "./catalog-service/catalog-service\n",
        encoding="utf-8",
    )
    start.chmod(0o755)


def build(out_root: Path) -> Path:
    os_name, arch = _platform_slug()
    package_name = f"material-tags-catalog-{os_name}-{arch}"
    stage = out_root / package_name
    pyi_dist = out_root / "_pyi_dist"
    pyi_work = out_root / "_pyi_work"

    for path in (stage, pyi_dist, pyi_work):
        if path.exists():
            shutil.rmtree(path)
    stage.mkdir(parents=True)

    serve_dir = _pyinstaller(
        "catalog-service",
        ROOT / "scripts" / "packaging" / "entry_serve.py",
        pyi_dist,
        pyi_work,
    )
    build_dir = _pyinstaller(
        "build-catalog",
        ROOT / "scripts" / "packaging" / "entry_build.py",
        pyi_dist,
        pyi_work,
    )

    shutil.copytree(serve_dir, stage / "catalog-service")
    shutil.copytree(build_dir, stage / "build-catalog")
    shutil.copy2(ROOT / ".env.example", stage / ".env.example")
    shutil.copy2(ROOT / ".env.example", stage / "catalog-service" / ".env.example")
    shutil.copy2(ASSETS / "README.txt", stage / "README.txt")
    _write_start_scripts(stage, os_name)

    zip_path = out_root / f"{package_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in stage.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(out_root).as_posix())

    print(f"package_dir={stage}")
    print(f"zip={zip_path}")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build portable zip")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "dist",
        help="输出目录（默认 dist/）",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    build(args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
