"""Tests for vdesktop_plugin.launchers.firefox — pure argv builders.

Note: firefox.py transitively imports ctypes.windll via _common, so these
tests are Windows-only (they cannot run on Linux/macOS). Same pattern and
caveat as test_terminal_args.py.
"""
from __future__ import annotations

from vdesktop_plugin.launchers.firefox import build_firefox_args


# --- build_firefox_args -----------------------------------------------------


def test_build_firefox_args_passes_no_remote_and_profile_first():
    """``-no-remote`` and ``-profile <dir>`` must precede ``-new-window`` so
    Firefox parses them as global flags before dispatching the URL list."""
    args = build_firefox_args(
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        ["https://example.com"],
        profile_dir=r"C:\Users\x\AppData\Local\Temp\vdesktop-firefox-abc",
    )

    no_remote = args.index("-no-remote")
    profile_flag = args.index("-profile")
    new_window = args.index("-new-window")

    assert no_remote < profile_flag < new_window


def test_build_firefox_args_profile_value_follows_flag():
    args = build_firefox_args(
        "firefox.exe",
        ["https://example.com"],
        profile_dir=r"C:\tmp\vd-ff-xyz",
    )
    assert args[args.index("-profile") + 1] == r"C:\tmp\vd-ff-xyz"


def test_build_firefox_args_appends_urls_at_end():
    args = build_firefox_args(
        "firefox.exe",
        ["https://a.example", "https://b.example"],
        profile_dir=r"C:\tmp\vd-ff",
    )
    assert args[-2:] == ["https://a.example", "https://b.example"]


def test_build_firefox_args_full_shape():
    args = build_firefox_args(
        "firefox.exe",
        ["https://example.com"],
        profile_dir=r"C:\tmp\vd-ff",
    )
    assert args == [
        "firefox.exe",
        "-no-remote",
        "-profile",
        r"C:\tmp\vd-ff",
        "-new-window",
        "https://example.com",
    ]


def test_build_firefox_args_single_url():
    args = build_firefox_args(
        "firefox.exe",
        ["https://only.example"],
        profile_dir=r"C:\tmp\vd-ff",
    )
    # Exactly one URL token at the tail.
    assert args[-1] == "https://only.example"
    assert args.count("https://only.example") == 1
