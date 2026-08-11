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


def package_basename(version: str, os_name: str, arch: str) -> str:
    """便携包顶层目录名与 zip basename（不含 .zip）。"""
    return f"material-tags-catalog-{version}-{os_name}-{arch}"


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


def _read_package_version() -> str:
    """读取已注入的 __version__（CI 从 tag 写入；本地多为 0.0.0+local）。"""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.catalog_service._version import __version__

    return __version__


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


def upgrade_asset_names(os_name: str) -> list[str]:
    """便携包根目录应拷贝的升级脚本文件名（相对 assets/）。"""
    if os_name == "windows":
        return ["upgrade.bat", "upgrade.ps1"]
    if os_name == "macos":
        return ["upgrade.command"]
    return []


def _write_upgrade_scripts(stage: Path, os_name: str) -> None:
    """拷贝 GitHub Release 一键升级脚本到包根。"""
    for name in upgrade_asset_names(os_name):
        src = ASSETS / name
        dest = stage / name
        shutil.copy2(src, dest)
        if name.endswith(".command"):
            dest.chmod(0o755)


def _write_start_scripts(stage: Path, os_name: str) -> None:
    """包根维护 .env；启动时复制到 exe 旁（frozen 从 exe 目录读）。"""
    if os_name == "windows":
        # 单一真相：assets/start.bat（含关闭 CMD 快速编辑）
        shutil.copy2(ASSETS / "start.bat", stage / "start.bat")
        _write_upgrade_scripts(stage, os_name)
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
    _write_upgrade_scripts(stage, os_name)


def build(out_root: Path) -> Path:
    os_name, arch = _platform_slug()
    version = _read_package_version()
    package_name = package_basename(version, os_name, arch)
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
    # frozen serve 旁挂 playbook，供 GET /v1/docs/llm-media-search-playbook
    playbook_src = ROOT / "docs" / "workflows" / "llm-media-search-playbook.md"
    playbook_dest_dir = stage / "catalog-service" / "docs" / "workflows"
    playbook_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(playbook_src, playbook_dest_dir / playbook_src.name)
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
