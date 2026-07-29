"""便携包命名纯函数测试（不跑 PyInstaller）。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILD_PORTABLE = ROOT / "scripts" / "packaging" / "build_portable.py"


def _load_build_portable():
    spec = importlib.util.spec_from_file_location("build_portable", BUILD_PORTABLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_basename_windows_amd64() -> None:
    mod = _load_build_portable()
    assert (
        mod.package_basename("0.2.0", "windows", "amd64")
        == "material-tags-catalog-0.2.0-windows-amd64"
    )


def test_package_basename_macos_arm64() -> None:
    mod = _load_build_portable()
    assert (
        mod.package_basename("0.2.0", "macos", "arm64")
        == "material-tags-catalog-0.2.0-macos-arm64"
    )


def test_package_basename_ci_local_version() -> None:
    mod = _load_build_portable()
    assert (
        mod.package_basename("0.0.0+ci.abc1234", "windows", "amd64")
        == "material-tags-catalog-0.0.0+ci.abc1234-windows-amd64"
    )
