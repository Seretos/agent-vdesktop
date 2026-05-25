"""launch_app (generic) MCP tool."""
from __future__ import annotations

from typing import Optional, Union

from .._engine import MANAGER


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
                Use when PID-based lookup is unreliable. Singleton-process apps
                — Notepad, Explorer, UWP apps, Firefox, and other browsers —
                immediately hand off to an existing instance when launched, so
                the spawned PID exits and PID-based resolution fails for them.
                For these apps ``title_contains`` identification is required.
        """
        return MANAGER.launch_app(
            executable, args, cwd, slot, desktop, label, identification
        )
