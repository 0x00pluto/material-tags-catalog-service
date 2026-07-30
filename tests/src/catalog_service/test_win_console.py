"""win_console.disable_quick_edit 单测。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.catalog_service.win_console import disable_quick_edit


def test_disable_quick_edit_non_windows() -> None:
    with patch("src.catalog_service.win_console.sys.platform", "darwin"):
        assert disable_quick_edit() is False


def test_disable_quick_edit_windows_success() -> None:
    kernel32 = MagicMock()
    kernel32.GetStdHandle.return_value = 42
    kernel32.GetConsoleMode.side_effect = lambda _h, mode_ref: (
        setattr(mode_ref, "value", 0x40 | 0x80 | 0x7) or True
    )
    kernel32.SetConsoleMode.return_value = True

    fake_ctypes = MagicMock()
    fake_ctypes.windll.kernel32 = kernel32
    fake_ctypes.byref = lambda x: x
    fake_ctypes.c_uint = lambda: MagicMock(value=0)

    with (
        patch("src.catalog_service.win_console.sys.platform", "win32"),
        patch.dict("sys.modules", {"ctypes": fake_ctypes}),
    ):
        # re-import path: disable_quick_edit imports ctypes inside the function
        assert disable_quick_edit() is True

    kernel32.GetStdHandle.assert_called_once_with(-10)
    kernel32.SetConsoleMode.assert_called_once()
    new_mode = kernel32.SetConsoleMode.call_args[0][1]
    assert new_mode & 0x40 == 0
    assert new_mode & 0x80 == 0x80


def test_disable_quick_edit_windows_already_off() -> None:
    mode_holder = MagicMock(value=0x80 | 0x7)  # quick-edit already clear
    kernel32 = MagicMock()
    kernel32.GetStdHandle.return_value = 42
    kernel32.GetConsoleMode.side_effect = lambda _h, mode_ref: (
        setattr(mode_ref, "value", mode_holder.value) or True
    )

    fake_ctypes = MagicMock()
    fake_ctypes.windll.kernel32 = kernel32
    fake_ctypes.byref = lambda x: x
    fake_ctypes.c_uint = lambda: MagicMock(value=0)

    with (
        patch("src.catalog_service.win_console.sys.platform", "win32"),
        patch.dict("sys.modules", {"ctypes": fake_ctypes}),
    ):
        assert disable_quick_edit() is True

    kernel32.SetConsoleMode.assert_not_called()


def test_disable_quick_edit_windows_no_console() -> None:
    kernel32 = MagicMock()
    kernel32.GetStdHandle.return_value = 0

    fake_ctypes = MagicMock()
    fake_ctypes.windll.kernel32 = kernel32
    fake_ctypes.c_uint = lambda: MagicMock(value=0)

    with (
        patch("src.catalog_service.win_console.sys.platform", "win32"),
        patch.dict("sys.modules", {"ctypes": fake_ctypes}),
    ):
        assert disable_quick_edit() is False


def test_disable_quick_edit_windows_api_raises() -> None:
    fake_ctypes = MagicMock()
    fake_ctypes.windll.kernel32.GetStdHandle.side_effect = OSError("boom")

    with (
        patch("src.catalog_service.win_console.sys.platform", "win32"),
        patch.dict("sys.modules", {"ctypes": fake_ctypes}),
    ):
        assert disable_quick_edit() is False
