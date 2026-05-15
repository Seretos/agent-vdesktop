"""Generic launcher for any executable. Used as a fallback when no specialized
launcher fits the user's request.

Note on singleton apps (Chrome, Firefox, Windows Terminal, etc.): when their
.exe is invoked, it forwards over IPC to an existing master process and the
spawn PID exits, so PID-based HWND resolution silently grabs the wrong
window. A bare ``class_name`` filter is rarely unique enough to disambiguate.
Use the dedicated launchers (``launch_chrome``, ``launch_firefox``,
``launch_terminal``) for those apps — they force standalone processes via
fresh profile / user-data dirs or unique window titles. ``launch_app``
remains the right tool only for non-singleton .exes or when the caller is
prepared to supply tight ``identification`` hints.
"""
from __future__ import annotations

import logging
from typing import Optional, Union

from ..pathmap import to_windows
from ._common import launch_and_register

log = logging.getLogger("vdesktop.launcher.generic")


def register(mcp) -> None:
    @mcp.tool()
    def launch_app(
        executable: str,
        args: Optional[list[str]] = None,
        cwd: Optional[str] = None,
        slot: Optional[str] = None,
        desktop: Optional[Union[int, str]] = None,
        label: Optional[str] = None,
        identification: Optional[dict] = None,
    ) -> dict:
        """Launch an arbitrary executable and adopt the resulting window.

        Args:
            executable: Path to the .exe (POSIX paths are translated).
            args: Additional command-line arguments.
            cwd: Working directory (POSIX paths are translated).
            slot: slot_id from the last apply_layout.
            desktop: Target desktop reference.
            label: Optional label.
            identification: Optional HWND-resolution hint:
                {"title_contains": str?, "class_name": str?, "timeout_ms": int}.
                Use when PID-based lookup is unreliable (e.g. apps that hand
                off to a singleton process and exit).
        """
        exe = to_windows(executable) if executable.startswith("/") else executable
        cmd: list[str] = [exe]
        if args:
            cmd.extend(args)
        cwd_win = to_windows(cwd) if cwd else None

        ident = identification or {}
        title_hint = ident.get("title_contains")
        class_filter = ident.get("class_name")
        timeout = int(ident.get("timeout_ms", 8000))

        return launch_and_register(
            args=cmd,
            app_type="generic",
            label=label,
            slot=slot,
            desktop=desktop,
            cwd=cwd_win,
            title_hint=title_hint,
            class_filter=class_filter,
            resolve_timeout_ms=timeout,
            pre_spawn_snapshot=bool(class_filter),
        )
