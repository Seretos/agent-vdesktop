"""MCP tools for window operations. Thin wrappers over
lib_python_vdesktop.VDesktopManager."""
from __future__ import annotations

from typing import Optional, Union

from ._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool()
    def list_windows(
        desktop: Optional[Union[int, str]] = None,
        include_unmanaged: bool = True,
    ) -> list[dict]:
        """List windows on the virtual desktop.

        By default, both managed and unmanaged top-level windows are returned
        (include_unmanaged=True). Pass include_unmanaged=False to restrict
        results to tracked (registry) windows only.

        Filters by desktop GUID if `desktop` is given.

        Every row contains a boolean discriminator key `tracked`:
          - tracked=True  — the window is in the tracking registry.
          - tracked=False — the window is unmanaged (visible on this desktop
            but not tracked by the registry).

        Fields present on ALL rows:
          hwnd, pid, title, app_type, desktop_guid, bounds.

        Additional fields present only when tracked=True:
          handle_id, label, slot_id, state, is_pinned, is_app_pinned.
          Pin fields are None when pyvda is unavailable. A pinned window is
          visible on every desktop, even though desktop_guid still reports
          its owning desktop.
          pid is null for tracked windows when the PID is unknown (Win32
          returns 0 for the PID in some cases; this wrapper normalises that
          to null rather than returning the misleading value 0).

        Fields present only when tracked=False (i.e. unmanaged rows):
          class_name.
          The tracked-window fields handle_id, label, slot_id, state,
          is_pinned, and is_app_pinned are absent from unmanaged rows.
        """
        rows = MANAGER.list_windows(desktop, include_unmanaged)
        for row in rows:
            if "handle_id" in row:
                row["tracked"] = True
                if row.get("pid") == 0:
                    row["pid"] = None
            else:
                row["tracked"] = False
        return rows

    @mcp.tool()
    def move_window(handle_id: str, target: dict) -> dict:
        """Move a tracked window.

        `target` keys (combinable):
          - "slot": slot_id from the last apply_layout (uses last layout for the
            window's current desktop, or the global last layout).
          - "bounds": explicit {x, y, w, h}.
          - "desktop": move the window to a different desktop (int index, name,
            or GUID).
        """
        return MANAGER.move_window(handle_id, target)

    @mcp.tool()
    def resize_window(handle_id: str, bounds: dict) -> dict:
        """Resize/reposition a tracked window to the given visible bounds
        (DWM shadows compensated)."""
        return MANAGER.resize_window(handle_id, bounds)

    @mcp.tool()
    def close_window(handle_id: str, force: bool = False) -> dict:
        """Send WM_CLOSE to the window. Removes it from the registry."""
        return MANAGER.close_window(handle_id, force)

    @mcp.tool()
    def focus_window(handle_id: str) -> dict:
        """Bring a tracked window to the foreground. Switches virtual desktops
        first if the window is on a different one."""
        return MANAGER.focus_window(handle_id)

    @mcp.tool()
    def relabel_window(handle_id: str, new_label: str) -> dict:
        """Change (or clear) a tracked window's label.

        Pass an empty string ``""`` to clear the label. Any non-empty string —
        including the literal ``"null"`` — is stored verbatim as the new label.
        """
        return MANAGER.relabel_window(handle_id, new_label or None)

    @mcp.tool()
    def minimize_window(handle_id: str) -> dict:
        """Minimize a tracked window."""
        return MANAGER.minimize_window(handle_id)

    @mcp.tool()
    def maximize_window(handle_id: str) -> dict:
        """Maximize a tracked window."""
        return MANAGER.maximize_window(handle_id)

    @mcp.tool()
    def restore_window(handle_id: str) -> dict:
        """Restore a tracked window to its normal (un-min/maximized) state."""
        return MANAGER.restore_window(handle_id)
