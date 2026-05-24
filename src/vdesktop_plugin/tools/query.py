"""MCP tools for title/tab window queries. Thin wrappers over
lib_python_vdesktop.VDesktopManager."""
from __future__ import annotations

from typing import Optional, Union

from ._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool()
    def find_window_by_title(
        pattern: str,
        desktop: Optional[Union[int, str]] = None,
        regex: bool = False,
    ) -> list[dict]:
        """Enumerate visible top-level windows whose title matches `pattern`.

        Browser windows (Chrome, Edge, Firefox) only put the **active tab**
        into their window title — an inactive Chrome tab named "GitHub" will
        NOT show up here unless that tab is in the foreground of its window.
        For searching across all Chrome tabs (including background ones),
        use `find_chrome_tab` instead.

        Args:
            pattern: Substring (default) or regex (if regex=True).
            desktop: Optional desktop filter.
            regex: Treat pattern as a Python regex.
        Returns:
            List of {hwnd, title, class_name, desktop_guid, handle_id?}.
            handle_id is set when the window is already in the registry.
        """
        return MANAGER.find_window_by_title(pattern, desktop, regex)

    @mcp.tool()
    def find_chrome_tab(
        pattern: str,
        regex: bool = False,
    ) -> list[dict]:
        """Search the tab strips of *all* Chrome windows for a tab whose title
        contains (or matches as regex) `pattern`. Uses UI Automation (UIA).

        Coverage depends on Chrome's accessibility tree, which is OFF by
        default:

        - **Active tab (always works)**: each visible Chrome window's active
          tab title is reflected in its OS window title, so we always find
          it via a title-substring fallback. Results from this path have
          ``tab_index = -1`` and ``tab_title == window_title``.
        - **Inactive/background tabs (requires accessibility ON)**: UIA can
          only enumerate the per-tab titles when Chrome's accessibility tree
          is built. Enable it once via ``chrome://accessibility/``
          (set "Web accessibility" to "On"), or relaunch Chrome with
          ``--force-renderer-accessibility``. Results from this path have
          ``tab_index >= 0`` and the real tab title.

        Returns ``[]`` when the pattern matches neither the active tab nor
        anything UIA exposes. If you expect a background tab to match,
        either:

          1. focus that tab so it becomes active and call again, or
          2. relaunch Chrome with ``--force-renderer-accessibility`` and
             call again.

        Returns:
            List of {handle_id, hwnd, tab_index, tab_title, window_title}.
            ``tab_index = -1`` means the match came from the window title
            (active tab fallback) rather than UIA enumeration. Adopts the
            matching Chrome window into the registry if it wasn't tracked
            yet (so the returned handle_id is immediately usable).
        """
        return MANAGER.find_chrome_tab(pattern, regex)
