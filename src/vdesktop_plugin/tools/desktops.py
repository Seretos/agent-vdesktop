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
        the desktop is renamed immediately (Windows 11).

        Index stability: the returned index is 0-based (Windows displays desktops
        as "Desktop 1", "Desktop 2", etc., which is 1-based). Both indices and
        auto-generated names shift after any delete or reorder and must not be
        used as stable references across operations. Use the "guid" field in
        the returned dict as the stable identifier when addressing a desktop
        programmatically.
        """
        return MANAGER.create_desktop(name)

    @mcp.tool()
    def delete_desktop(
        target: DesktopRef,
        fallback_desktop: Optional[DesktopRef] = None,
    ) -> dict:
        """Delete a virtual desktop. Windows moves its windows to `fallback_desktop`
        (or to the desktop on the left by default).

        Args:
            target: Identifies the desktop to delete. Accepted forms:
                - **index** (int): 0-based integer position (e.g. ``0`` for
                  the first desktop).
                - **name** (str): exact desktop name, whitespace-stripped
                  (e.g. ``"Work"``).
                - **GUID** (str): braced GUID string as returned by
                  ``list_desktops`` (e.g. ``"{3f7b2e1a-...}"``). The curly
                  braces are required — omitting them will fail to resolve.
                  Prefer GUID over index or name as the stable identifier,
                  because indices and auto-generated names shift after any
                  delete or reorder.

        Index stability: desktop indices are 0-based (Windows displays desktops
        as "Desktop 1", "Desktop 2", etc., which is 1-based). Both indices and
        auto-generated names shift after any delete or reorder and must not be
        used as stable references across operations. The response contains
        "deleted_guid" (the GUID of the removed desktop) and "remaining" (a
        list of surviving desktop dicts, each with a "guid" field). Use "guid"
        as the stable identifier when addressing desktops programmatically.

        Deleting the last/only desktop is not guarded: pyvda's ``desktop.remove()``
        will surface as a tool error (COM error) when called on the only remaining
        desktop.
        """
        return MANAGER.delete_desktop(target, fallback_desktop)

    @mcp.tool()
    def switch_to_desktop(target: DesktopRef) -> dict:
        """Switch the foreground to the given desktop.

        Args:
            target: Identifies the desktop to switch to. Accepted forms:
                - **index** (int): 0-based integer position (e.g. ``0`` for
                  the first desktop).
                - **name** (str): exact desktop name, whitespace-stripped
                  (e.g. ``"Work"``).
                - **GUID** (str): braced GUID string as returned by
                  ``list_desktops`` (e.g. ``"{3f7b2e1a-...}"``). The curly
                  braces are required — omitting them will fail to resolve.
                  Prefer GUID over index or name as the stable identifier,
                  because indices and auto-generated names shift after any
                  delete or reorder.
        """
        try:
            return MANAGER.switch_to_desktop(target)
        except ValueError as exc:
            if isinstance(target, str) and "Unknown desktop reference" in str(exc):
                desktops = MANAGER.list_desktops()
                n = len(desktops)
                raise ValueError(
                    f"Unknown desktop reference: {target!r} "
                    f"(have {n} desktop(s)). "
                    "Use list_desktops() to see valid names and GUIDs."
                ) from exc
            raise

    @mcp.tool()
    def rename_desktop(target: DesktopRef, new_name: str) -> dict:
        """Rename a virtual desktop. Windows 11 only.

        Args:
            target: Identifies the desktop to rename. Accepted forms:
                - **index** (int): 0-based integer position (e.g. ``0`` for
                  the first desktop).
                - **name** (str): exact desktop name, whitespace-stripped
                  (e.g. ``"Work"``).
                - **GUID** (str): braced GUID string as returned by
                  ``list_desktops`` (e.g. ``"{3f7b2e1a-...}"``). The curly
                  braces are required — omitting them will fail to resolve.
                  Prefer GUID over index or name as the stable identifier,
                  because indices and auto-generated names shift after any
                  delete or reorder.
            new_name: The new name to assign to the desktop.
        """
        return MANAGER.rename_desktop(target, new_name)

    # -- Pinning (cross-desktop visibility) ---------------------------------

    @mcp.tool()
    def pin_window_all_desktops(handle_id: str) -> dict:
        """Pin a tracked window so it is visible on every virtual desktop."""
        pre = MANAGER.is_pinned(handle_id)
        already_pinned = bool(pre.get("window_pinned"))
        result = MANAGER.pin_window_all_desktops(handle_id)
        result["already_pinned"] = already_pinned
        return result

    @mcp.tool()
    def unpin_window(handle_id: str) -> dict:
        """Unpin a tracked window."""
        return MANAGER.unpin_window(handle_id)

    @mcp.tool()
    def pin_app_all_desktops(handle_id: str) -> dict:
        """Pin the application (every window of its AppUserModelID) to all desktops.

        WARNING: this operation is app-wide. Windows resolves the AppUserModelID
        from the supplied handle and pins *every* open window of that application,
        not only the one referenced. Unrelated windows of the same app will become
        visible on all desktops. Use `pin_window_all_desktops` when you intend to
        pin a single window only."""
        return MANAGER.pin_app_all_desktops(handle_id)

    @mcp.tool()
    def unpin_app(handle_id: str) -> dict:
        """Unpin the application of the given window from all desktops.

        WARNING: this operation is app-wide. Windows resolves the AppUserModelID
        from the supplied handle and unpins *every* open window of that application,
        not only the one referenced. Unrelated windows of the same app will lose
        their cross-desktop visibility."""
        return MANAGER.unpin_app(handle_id)

    @mcp.tool()
    def is_pinned(handle_id: str) -> dict:
        """Return both the window-pinned and app-pinned state for a tracked window.

        This tool requires a handle_id, which only exists for windows that are
        already in the tracking registry. Windows returned by
        ``find_window_by_title`` and unmanaged rows from ``list_windows`` carry
        an ``hwnd`` (OS integer) but no handle_id, so they cannot be passed here
        directly.

        If the window is already tracked, ``list_windows()`` already includes
        ``is_pinned`` and ``is_app_pinned`` on every tracked row — no separate
        ``is_pinned`` call is needed in that case.

        For an untracked window, call ``adopt_window(hwnd)`` first to register
        it and obtain a handle_id, then pass that handle_id here.
        """
        return MANAGER.is_pinned(handle_id)
