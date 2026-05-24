"""launch_vscode MCP tool."""
from __future__ import annotations

from typing import Optional, Union

from .._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool()
    def launch_vscode(
        folder: str,
        files: Optional[list[dict]] = None,
        slot: Optional[str] = None,
        desktop: Optional[Union[int, str]] = None,
        label: Optional[str] = None,
        reuse_window: bool = False,
    ) -> dict:
        """Launch VS Code on a folder (and optionally open specific files).

        Args:
            folder: Folder to open. POSIX paths are translated for WSL use.
            files: Optional list of {"path": str, "line": int?} to open inside.
            slot: slot_id from the last apply_layout.
            desktop: Target desktop reference.
            label: Optional label.
            reuse_window: If False (default) pass `-n` to force a new VS Code
                window — guarantees a distinct HWND.
        """
        return MANAGER.launch_vscode(folder, files, slot, desktop, label, reuse_window)
