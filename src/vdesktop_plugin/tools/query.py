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
            ``hwnd`` is the OS-level integer window handle and is always
            present. ``handle_id`` is a registry string key and is only
            present (non-null) when the window is already in the tracking
            registry. A null handle_id means the window is untracked — you
            cannot pass it to tools that require a handle_id (such as
            ``is_pinned``, ``move_window``, etc.). Call
            ``adopt_window(hwnd)`` first to obtain a handle_id for an
            untracked window.
        """
        return MANAGER.find_window_by_title(pattern, desktop, regex)

    @mcp.tool()
    def find_chrome_tab(
        pattern: str,
        regex: bool = False,
    ) -> list[dict]:
        """**WRITE SIDE-EFFECT**: This tool unconditionally ADOPTS the matched
        Chrome window into the tracking registry on every call. Adoption is a
        persistent write operation — the window remains tracked until you
        explicitly call ``release_window``. Call ``list_windows`` to see
        currently-tracked windows.

        Search the tab strips of *all* Chrome windows for a tab whose title
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
        anything UIA exposes. An empty result is ambiguous: it can mean no
        Chrome windows were open at all, no tab title matched the pattern,
        OR accessibility was off and no active (foreground) tab matched —
        these three cases are indistinguishable from the return value alone.
        Use ``find_window_by_title`` to verify Chrome windows are actually
        visible before concluding there is no match. If you expect a
        background tab to match, either:

          1. focus that tab so it becomes active and call again, or
          2. relaunch Chrome with ``--force-renderer-accessibility`` and
             call again.

        Returns:
            List of {handle_id, hwnd, tab_index, tab_title, window_title,
            adopted}. ``tab_index = -1`` on every result means UIA tab
            enumeration did not run — either accessibility was off or the
            tab strip was inaccessible — and only the active-tab window-title
            fallback was used. ``tab_index >= 0`` means UIA enumerated the
            tab strip and the real per-tab title was matched.
            ``adopted`` is ``True`` when THIS call added the window to the
            tracking registry; ``False`` when the window was already tracked
            before this call.
        """
        pre_tracked = {w["hwnd"] for w in MANAGER.list_windows()}
        results = MANAGER.find_chrome_tab(pattern, regex)
        for result in results:
            result["adopted"] = result["hwnd"] not in pre_tracked
        return results
