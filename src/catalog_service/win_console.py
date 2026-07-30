"""Windows 控制台模式辅助（防 CMD 快速编辑假死）。"""

from __future__ import annotations

import sys

# Win32 console mode bits（与 start.bat 一致）
_ENABLE_QUICK_EDIT_MODE = 0x40
_ENABLE_EXTENDED_FLAGS = 0x80
_STD_INPUT_HANDLE = -10
_INVALID_HANDLE_VALUE = -1


def disable_quick_edit() -> bool:
    """关闭当前控制台的快速编辑模式。

    仅影响本进程附着的控制台窗口，不改注册表。
    非 Windows、无控制台或 API 失败时返回 False，不抛异常。
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(_STD_INPUT_HANDLE)
        if handle in (0, _INVALID_HANDLE_VALUE):
            return False

        mode = ctypes.c_uint()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False

        new_mode = (mode.value & ~_ENABLE_QUICK_EDIT_MODE) | _ENABLE_EXTENDED_FLAGS
        if new_mode == mode.value:
            return True
        return bool(kernel32.SetConsoleMode(handle, new_mode))
    except Exception:  # noqa: BLE001
        return False
