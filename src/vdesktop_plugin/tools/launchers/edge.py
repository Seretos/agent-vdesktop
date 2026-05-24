"""launch_edge MCP tool."""
from __future__ import annotations

from typing import Optional, Union

from .._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool()
    def launch_edge(
        urls: list[str],
        slot: Optional[str] = None,
        desktop: Optional[Union[int, str]] = None,
        label: Optional[str] = None,
        new_user_data_dir: bool = True,
        inprivate: bool = False,
    ) -> dict:
        """Launch Microsoft Edge with one or more tabs in a NEW window.

        Args:
            urls: List of URLs to open as separate tabs.
            slot: Optional slot_id from the last apply_layout to place the window in.
            desktop: Optional target desktop (index, name, or GUID).
            label: Optional human-readable label for later reference.
            new_user_data_dir: REQUIRED True (default) to guarantee a distinct
                browser process — without this, Edge may IPC to an existing
                instance and the spawn PID exits before HWND resolution.
            inprivate: Open in InPrivate mode.
        Returns:
            {handle_id, hwnd, pid, label, app_type, desktop_guid, slot_id, bounds, title}
        """
        return MANAGER.launch_edge(
            urls, slot, desktop, label, new_user_data_dir, inprivate
        )
