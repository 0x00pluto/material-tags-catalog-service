"""定位并渲染 LLM 媒体检索 playbook Markdown（开发仓 / 便携包）。"""

from __future__ import annotations

import sys
from pathlib import Path

PLAYBOOK_REL = Path("docs") / "workflows" / "llm-media-search-playbook.md"
FILE_BASE_UNSET = "（未配置 FILE_BROWSER_BASE）"


def normalize_file_browser_base(value: object | None) -> str | None:
    """strip + 去尾斜杠；空串 → None。Settings 与 render 共用。"""
    if value is None:
        return None
    text = str(value).strip().rstrip("/")
    return text or None


def resolve_playbook_markdown_path() -> Path | None:
    """返回可读的 playbook 文件路径；找不到则 None。"""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / PLAYBOOK_REL)
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / PLAYBOOK_REL)
    # src/catalog_service/playbook_docs.py → 仓库根
    pkg_file = Path(__file__).resolve()
    candidates.append(pkg_file.parents[2] / PLAYBOOK_REL)
    # cwd 兜底（从仓库根启动时）
    candidates.append(Path.cwd() / PLAYBOOK_REL)

    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def render_playbook(
    template: str,
    *,
    api_base: str,
    file_base: str | None,
) -> str:
    """替换模板占位符；file_base 空则写入未配置文案。"""
    api = str(api_base).strip().rstrip("/")
    fb = normalize_file_browser_base(file_base) or FILE_BASE_UNSET
    return template.replace("{{api_base}}", api).replace("{{file_base}}", fb)
