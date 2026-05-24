"""launch_terminal MCP tool."""
from __future__ import annotations

from typing import Optional, Union

from .._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool()
    def launch_terminal(
        tabs: list[dict],
        slot: Optional[str] = None,
        desktop: Optional[Union[int, str]] = None,
        label: Optional[str] = None,
        window_title: Optional[str] = None,
    ) -> dict:
        """Launch Windows Terminal (wt.exe) with one or more tabs.

        Each tab is a dict:
          {"profile": str?, "cwd": str?, "command": str?,
           "shell": "powershell"|"cmd"|"wsl"|None, "wsl_distro": str?}

        Examples:
          tabs=[{"shell": "wsl", "wsl_distro": "Ubuntu", "cwd": "/home/test"}]
          tabs=[{"shell": "powershell", "cwd": "E:\\\\development", "command": "claude"}]

        A unique --title tag is injected so we can reliably resolve the new
        window (wt.exe forwards to a singleton; the spawn PID exits).

        Security:
          The ``command`` field is executed by the chosen shell (powershell.exe,
          cmd.exe, or bash via wsl.exe) and accepts arbitrary shell code by
          design. ``profile``, ``wsl_distro``, and ``window_title`` are
          restricted to a safe identifier charset. See SECURITY.md for the
          full threat model.
        """
        return MANAGER.launch_terminal(tabs, slot, desktop, label, window_title)
