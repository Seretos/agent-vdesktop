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
        env: Optional[dict[str, str]] = None,
        wsl_distro: Optional[str] = None,
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
            env: Optional mapping of environment variables to overlay on the
                process environment. When supplied the process inherits a full
                copy of os.environ with these keys overlaid. Pass None (default)
                to inherit the environment unchanged.
            wsl_distro: Optional WSL distribution name used to resolve POSIX
                paths in ``folder`` and ``files``. Defaults to the calling WSL
                distro when the tool is invoked from within WSL; pass a name
                (e.g. ``"Ubuntu"``) to override which distro the path mapping
                is resolved against. Pass None (default) to let the engine
                detect the calling distro automatically.
        """
        return MANAGER.launch_vscode(folder, files, slot, desktop, label, reuse_window, env=env, wsl_distro=wsl_distro)
