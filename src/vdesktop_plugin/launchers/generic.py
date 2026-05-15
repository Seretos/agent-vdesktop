"""Generic launcher for any executable. Used as a fallback when no specialized
launcher fits the user's request."""
from __future__ import annotations

import logging
import os
from typing import Optional, Union

from ..pathmap import to_windows
from ._common import launch_and_register

log = logging.getLogger("vdesktop.launcher.generic")


def _resolve_working_directory(working_directory: Optional[str]) -> Optional[str]:
    """Translate (if POSIX) and validate the requested working directory.

    Returns the Windows-style absolute path to hand to ``subprocess.Popen``,
    or ``None`` when the caller wants the MCP process's cwd. Raises
    ``ValueError`` early — before any spawn happens — if the path does not
    point at an existing directory; this catches typos at the API surface
    instead of surfacing them as opaque CreateProcess errors deep in the
    pipeline.
    """
    if working_directory is None:
        return None
    cwd_win = to_windows(working_directory)
    if not os.path.exists(cwd_win):
        raise ValueError(
            f"working_directory does not exist: {working_directory!r} "
            f"(resolved to {cwd_win!r})"
        )
    if not os.path.isdir(cwd_win):
        raise ValueError(
            f"working_directory is not a directory: {working_directory!r} "
            f"(resolved to {cwd_win!r})"
        )
    return cwd_win


def register(mcp) -> None:
    @mcp.tool()
    def launch_app(
        executable: str,
        args: Optional[list[str]] = None,
        working_directory: Optional[str] = None,
        slot: Optional[str] = None,
        desktop: Optional[Union[int, str]] = None,
        label: Optional[str] = None,
        identification: Optional[dict] = None,
    ) -> dict:
        """Launch an arbitrary executable and adopt the resulting window.

        Args:
            executable: Path to the .exe (POSIX paths are translated).
            args: Additional command-line arguments.
            working_directory: Optional working directory for the spawned
                process. POSIX paths are translated for WSL use. When
                ``None`` (default) the spawned process inherits the MCP
                server's current working directory — this preserves the
                pre-issue-#7 behaviour. The path is validated **before**
                spawn: a non-existent or non-directory path raises
                ``ValueError`` so typos surface at the API boundary
                instead of as cryptic CreateProcess failures.
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
        cwd_win = _resolve_working_directory(working_directory)

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
