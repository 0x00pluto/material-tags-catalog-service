"""应用配置（环境变量 / .env）。"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.catalog_service.models import CATALOG_FILENAME


def resolve_env_file() -> Path:
    """开发态用 cwd/.env；PyInstaller 冻结态用 exe 同目录 .env。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / ".env"
    return Path(".env")


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

    def resolved_out(self) -> Path:
        if self.catalog_out is not None:
            return self.catalog_out
        return self.catalog_root / CATALOG_FILENAME
