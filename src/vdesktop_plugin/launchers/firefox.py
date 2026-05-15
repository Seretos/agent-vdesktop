"""Firefox launcher.

Firefox is a singleton like Chrome: ``firefox.exe -new-window`` without further
hints IPCs into the existing master process, which then asks an existing
window to open a new one and the spawn PID exits. PID-based HWND resolution
fails, and a bare ``MozillaWindowClass`` filter cannot distinguish the new
window from any other Firefox window the user already had open.

We force a standalone Firefox process — and therefore a stable spawn PID —
with ``-no-remote -profile <fresh-tmp>``. That mirrors the trick
``launch_chrome`` uses with ``--user-data-dir`` and keeps the same DX.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional, Union

from .._window_classes import FIREFOX_WINDOW_CLASS
from ._common import launch_and_register

log = logging.getLogger("vdesktop.launcher.firefox")

_FIREFOX_CANDIDATES = [
    r"C:\Program Files\Mozilla Firefox\firefox.exe",
    r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"),
]


def find_firefox() -> str:
    for path in _FIREFOX_CANDIDATES:
        if path and os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "firefox.exe not found. Install Mozilla Firefox or set the path explicitly via launch_app."
    )


def build_firefox_args(
    firefox: str,
    urls: list[str],
    *,
    profile_dir: str,
) -> list[str]:
    """Compose the firefox.exe argv that forces a standalone process.

    The order matters: ``-no-remote`` must precede ``-profile`` so Firefox's
    parser treats them as global flags before it dispatches the URLs.
    """
    args = [firefox, "-no-remote", "-profile", profile_dir, "-new-window"]
    args.extend(urls)
    return args


def register(mcp) -> None:
    @mcp.tool()
    def launch_firefox(
        urls: list[str],
        slot: Optional[str] = None,
        desktop: Optional[Union[int, str]] = None,
        label: Optional[str] = None,
    ) -> dict:
        """Launch Mozilla Firefox with one or more tabs in a NEW window.

        Forces a standalone Firefox process via ``-no-remote -profile
        <fresh-tmp>`` so the spawn PID survives long enough for HWND
        resolution. The profile directory is always a fresh
        ``tempfile.mkdtemp`` — there is no persistent profile, no Login
        sessions, no extensions; this mirrors ``launch_chrome``'s
        behaviour with ``--user-data-dir``.

        For Firefox launches that should reuse an existing profile or
        share state with an already-open browser, use the generic
        ``launch_app`` tool instead and accept the singleton-PID
        caveats it documents.

        Args:
            urls: List of URLs to open as separate tabs.
            slot: Optional slot_id from the last apply_layout.
            desktop: Optional target desktop (index, name, or GUID).
            label: Optional human-readable label.

        Returns:
            {handle_id, hwnd, pid, label, app_type, desktop_guid,
             slot_id, bounds, title}
        """
        if not urls:
            raise ValueError("launch_firefox requires at least one URL")
        firefox = find_firefox()
        profile_dir = tempfile.mkdtemp(prefix="vdesktop-firefox-")
        args = build_firefox_args(firefox, urls, profile_dir=profile_dir)

        return launch_and_register(
            args=args,
            app_type="firefox",
            label=label,
            slot=slot,
            desktop=desktop,
            class_filter=FIREFOX_WINDOW_CLASS,
            resolve_timeout_ms=15000,
            pre_spawn_snapshot=True,
        )
