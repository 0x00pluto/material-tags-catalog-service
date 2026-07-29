"""升级脚本资产拷贝清单与写入（不跑 PyInstaller）。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILD_PORTABLE = ROOT / "scripts" / "packaging" / "build_portable.py"
ASSETS = ROOT / "scripts" / "packaging" / "assets"


def _load_build_portable():
    spec = importlib.util.spec_from_file_location("build_portable", BUILD_PORTABLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_asset_names_windows() -> None:
    mod = _load_build_portable()
    assert mod.upgrade_asset_names("windows") == ["upgrade.bat", "upgrade.ps1"]


def test_upgrade_asset_names_macos() -> None:
    mod = _load_build_portable()
    assert mod.upgrade_asset_names("macos") == ["upgrade.command"]


def test_upgrade_asset_names_unknown() -> None:
    mod = _load_build_portable()
    assert mod.upgrade_asset_names("linux") == []


def test_write_upgrade_scripts_windows(tmp_path: Path) -> None:
    mod = _load_build_portable()
    stage = tmp_path / "stage"
    stage.mkdir()
    mod._write_upgrade_scripts(stage, "windows")
    assert (stage / "upgrade.bat").is_file()
    assert (stage / "upgrade.ps1").is_file()
    assert not (stage / "upgrade.command").exists()
    # source assets exist
    assert (ASSETS / "upgrade.bat").is_file()
    assert (ASSETS / "upgrade.ps1").is_file()


def test_write_upgrade_scripts_macos(tmp_path: Path) -> None:
    mod = _load_build_portable()
    stage = tmp_path / "stage"
    stage.mkdir()
    mod._write_upgrade_scripts(stage, "macos")
    dest = stage / "upgrade.command"
    assert dest.is_file()
    assert dest.stat().st_mode & 0o111
    assert not (stage / "upgrade.bat").exists()
    assert (ASSETS / "upgrade.command").is_file()
