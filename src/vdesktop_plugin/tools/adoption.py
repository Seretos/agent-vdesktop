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
        and filtering to entries not present in the registry.

        When to prefer which: prefer ``list_unmanaged_windows`` when you
        specifically want only adoption candidates (unmanaged windows)
        pre-filtered; prefer ``list_windows()`` as the general default — it
        returns both tracked and unmanaged windows in one call without any
        pre-filtering.
        """
        return MANAGER.list_unmanaged_windows(desktop)

    @mcp.tool()
    def adopt_window(
        hwnd: int,
        label: Optional[str] = None,
        app_type_hint: Optional[Literal["chrome", "edge", "vscode", "terminal", "unknown"]] = None,
    ) -> dict:
        """Add an existing HWND to the registry so it can be moved, focused,
        labeled, and tracked like a launched window. Returns the new handle_id.

        The returned handle_id is the stable key for all subsequent window
        operations (``move_window``, ``focus_window``, ``pin_window_all_desktops``,
        etc.). After adoption, ``is_pinned(handle_id)`` is available for
        pin-state inspection without any extra steps.

        `app_type_hint` overrides the auto-classification — pass it when you
        know the window's identity. Accepted values: ``"chrome"``, ``"edge"``,
        ``"vscode"``, ``"terminal"``, ``"unknown"``."""
        result = MANAGER.adopt_window(hwnd, label, app_type_hint)
        result.setdefault("slot_id", None)
        return result

    @mcp.tool()
    def release_window(handle_id: str) -> dict:
        """Remove a tracked window from the registry. The window itself stays
        open and is removed from the tracking registry.

        Raises ``ValueError`` if ``handle_id`` is not a currently-tracked
        window (unknown or already released). Call ``list_windows()`` to see
        currently-tracked windows.
        """
        result = MANAGER.release_window(handle_id)
        if isinstance(result, dict) and result.get("released") is False:
            raise ValueError(
                f"Unknown or already-released handle_id: {handle_id!r}. "
                "Call list_windows() to see currently-tracked windows."
            )
        return result
