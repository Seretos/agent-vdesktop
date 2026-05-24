"""MCP tools for virtual-desktop operations. Thin wrappers over
lib_python_vdesktop.VDesktopManager."""
from __future__ import annotations

from typing import Optional, Union

from ._engine import MANAGER

DesktopRef = Union[int, str]


def register(mcp) -> None:
    @mcp.tool()
    def list_desktops() -> list[dict]:
        """List all virtual desktops with their index (0-based), name, GUID,
        and whether each is the currently active desktop."""
        return MANAGER.list_desktops()

    @mcp.tool()
    def get_current_desktop() -> dict:
        """Return the currently active virtual desktop."""
        return MANAGER.get_current_desktop()

    @mcp.tool()
    def create_desktop(name: Optional[str] = None) -> dict:
        """Create a new virtual desktop and return its info. If `name` is given,
        the desktop is renamed immediately (Windows 11)."""
        return MANAGER.create_desktop(name)

    @mcp.tool()
    def delete_desktop(
        target: DesktopRef,
        fallback_desktop: Optional[DesktopRef] = None,
    ) -> dict:
        """Delete a virtual desktop. Windows moves its windows to `fallback_desktop`
        (or to the desktop on the left by default)."""
        return MANAGER.delete_desktop(target, fallback_desktop)

    @mcp.tool()
    def switch_to_desktop(target: DesktopRef) -> dict:
        """Switch the foreground to the given desktop."""
        return MANAGER.switch_to_desktop(target)

    @mcp.tool()
    def rename_desktop(target: DesktopRef, new_name: str) -> dict:
        """Rename a virtual desktop. Windows 11 only."""
        return MANAGER.rename_desktop(target, new_name)

    # -- Pinning (cross-desktop visibility) ---------------------------------

    @mcp.tool()
    def pin_window_all_desktops(handle_id: str) -> dict:
        """Pin a tracked window so it is visible on every virtual desktop."""
        return MANAGER.pin_window_all_desktops(handle_id)

    @mcp.tool()
    def unpin_window(handle_id: str) -> dict:
        """Unpin a tracked window."""
        return MANAGER.unpin_window(handle_id)

    @mcp.tool()
    def pin_app_all_desktops(handle_id: str) -> dict:
        """Pin the application (every window of its app-user-model-ID) to all
        desktops, not just one window. Use `pin_window_all_desktops` for a
        single-window pin."""
        return MANAGER.pin_app_all_desktops(handle_id)

    @mcp.tool()
    def unpin_app(handle_id: str) -> dict:
        """Unpin the application of the given window."""
        return MANAGER.unpin_app(handle_id)

    @mcp.tool()
    def is_pinned(handle_id: str) -> dict:
        """Return both the window-pinned and app-pinned state for a tracked window."""
        return MANAGER.is_pinned(handle_id)
