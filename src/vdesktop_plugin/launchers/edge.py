"""Microsoft Edge launcher.

Same Chromium foundation as Chrome — distinct user-data-dir per launch is
required to guarantee a fresh master/browser process whose spawn PID maps to
the new window. Without `--user-data-dir`, msedge.exe IPCs to the existing
instance and exits, breaking PID-based HWND resolution.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional, Union

from .._window_classes import CHROME_WIDGET_CLASS
from ._common import launch_and_register

log = logging.getLogger("vdesktop.launcher.edge")

_EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]


def find_edge() -> str:
    for path in _EDGE_CANDIDATES:
        if path and os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "msedge.exe not found. Install Microsoft Edge or set the path explicitly via launch_app."
    )


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
        if not urls:
            raise ValueError("launch_edge requires at least one URL")
        edge = find_edge()
        args = [edge, "--new-window"]
        if inprivate:
            args.append("--inprivate")
        if new_user_data_dir:
            udd = tempfile.mkdtemp(prefix="vdesktop-edge-")
            args.extend(
                [
                    f"--user-data-dir={udd}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
            )
        args.extend(urls)

        return launch_and_register(
            args=args,
            app_type="edge",
            label=label,
            slot=slot,
            desktop=desktop,
            class_filter=CHROME_WIDGET_CLASS,
            resolve_timeout_ms=10000,
        )
