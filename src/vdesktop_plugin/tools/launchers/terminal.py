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
        env: Optional[dict[str, str]] = None,
    ) -> dict:
        """Launch Windows Terminal (wt.exe) with one or more tabs.

        Each tab is a dict:
          {"profile": str?, "cwd": str?, "command": str?,
           "shell": "powershell"|"cmd"|"wsl"|None, "wsl_distro": str?}

        Examples:
          tabs=[{"shell": "wsl", "wsl_distro": "Ubuntu", "cwd": "/home/test"}]
          tabs=[{"shell": "powershell", "cwd": "E:\\\\development", "command": "claude"}]

        A unique ``--title vdesktop-term-<hash>`` tag is injected so the new
        window can be reliably resolved (wt.exe forwards to a singleton; the
        spawn PID exits immediately). This title persists as the permanent OS
        window title after launch — it is what the OS and `find_window_by_title`
        will see. Do NOT rely on a human-friendly title to locate this terminal
        after launch; use the ``handle_id`` returned by this call instead.

        Security:
          The ``command`` field is executed by the chosen shell (powershell.exe,
          cmd.exe, or bash via wsl.exe) and accepts arbitrary shell code by
          design. ``profile``, ``wsl_distro``, and ``window_title`` are
          restricted to a safe identifier charset. See SECURITY.md for the
          full threat model.

        Args:
            tabs: List of tab descriptors (see dict shape above).
            slot: Optional slot_id from the last apply_layout.
            desktop: Optional target desktop reference.
            label: Optional human-readable label.
            window_title: Optional custom window title prefix.
            env: Optional mapping of environment variables to overlay on the
                process environment. When supplied the process inherits a full
                copy of os.environ with these keys overlaid. Pass None (default)
                to inherit the environment unchanged.
        """
        return MANAGER.launch_terminal(tabs, slot, desktop, label, window_title, env=env)
