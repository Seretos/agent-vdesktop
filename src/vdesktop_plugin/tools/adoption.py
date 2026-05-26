"""MCP tools for adopting/releasing external windows. Thin wrappers over
lib_python_vdesktop.VDesktopManager."""
from __future__ import annotations

from typing import Literal, Optional, Union

from ._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool()
    def list_unmanaged_windows(
        desktop: Optional[Union[int, str]] = None,
    ) -> list[dict]:
        """List visible top-level windows that are NOT currently in the
        registry. Useful before adopting external windows. Filter by desktop
        if given.

        This tool is equivalent to calling list_windows(include_unmanaged=True)
        and filtering to entries not present in the registry. For general window
        discovery, list_windows() is the recommended default starting point as it
        returns all windows (both tracked and unmanaged) in one call."""
        return MANAGER.list_unmanaged_windows(desktop)

    @mcp.tool()
    def adopt_window(
        hwnd: int,
        label: Optional[str] = None,
        app_type_hint: Optional[Literal["chrome", "edge", "vscode", "terminal", "unknown"]] = None,
    ) -> dict:
        """Add an existing HWND to the registry so it can be moved, focused,
        labeled, and tracked like a launched window. Returns the new handle_id.

        `app_type_hint` overrides the auto-classification — pass it when you
        know the window's identity. Accepted values: ``"chrome"``, ``"edge"``,
        ``"vscode"``, ``"terminal"``, ``"unknown"``."""
        return MANAGER.adopt_window(hwnd, label, app_type_hint)

    @mcp.tool()
    def release_window(handle_id: str) -> dict:
        """Remove a window from the registry. The window itself stays open."""
        return MANAGER.release_window(handle_id)
