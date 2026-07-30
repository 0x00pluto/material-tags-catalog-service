"""应用配置（环境变量 / .env）。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.catalog_service.models import CATALOG_FILENAME


def resolve_env_file() -> Path:
    """开发态用 cwd/.env；PyInstaller 冻结态用 exe 同目录 .env。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / ".env"
    return Path(".env")


def parse_exclude_dir_names(raw: str | Sequence[str] | None) -> frozenset[str]:
    """逗号分隔目录名 → frozenset；strip 空白，丢弃空 token。"""
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = [str(p) for p in raw]
    return frozenset(p.strip() for p in parts if p and str(p).strip())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    catalog_root: Path = Field(alias="CATALOG_ROOT")
    catalog_out: Path | None = Field(default=None, alias="CATALOG_OUT")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8787, alias="PORT")
    watch_enabled: bool = Field(default=True, alias="WATCH_ENABLED")
    watch_debounce_sec: float = Field(default=2.0, alias="WATCH_DEBOUNCE_SEC")
    schedule_enabled: bool = Field(default=True, alias="SCHEDULE_ENABLED")
    schedule_interval_sec: float = Field(default=600.0, alias="SCHEDULE_INTERVAL_SEC")
    api_key: str | None = Field(default=None, alias="API_KEY")
    # 逗号分隔；相对 root 任一路径段精确匹配则跳过该子树内标签（空=不排除）
    scan_exclude_dir_names: str = Field(default="", alias="SCAN_EXCLUDE_DIR_NAMES")
    # 合法 orphan（校验通过但无原媒体）是否物理删除标签文件
    purge_orphan_tags: bool = Field(default=True, alias="PURGE_ORPHAN_TAGS")

    def resolved_out(self) -> Path:
        if self.catalog_out is not None:
            return self.catalog_out
        return self.catalog_root / CATALOG_FILENAME

    def exclude_dir_name_set(self) -> frozenset[str]:
        return parse_exclude_dir_names(self.scan_exclude_dir_names)