"""Smoke test: every tool module registers its expected tools against a minimal
FastMCP stand-in.

This verifies the plugin wiring imports cleanly — which transitively imports
`lib_python_vdesktop` and instantiates `VDesktopManager` — and that the full
tool surface is wired with no missing or duplicate tools. It does NOT exercise
the COM/Win32 paths (those are verified manually on real hardware).

Windows-only: importing the engine touches ctypes.windll. That matches the
production CI runner.
"""
from __future__ import annotations

import typing


class FakeMCP:
    """Captures tool names and function references the way FastMCP's
    @mcp.tool() decorator would."""

    def __init__(self) -> None:
        self.tool_names: list[str] = []
        self.tool_fns: dict[str, object] = {}

    def tool(self, name: str | None = None):
        def deco(fn):
            tool_name = name or fn.__name__
            self.tool_names.append(tool_name)
            self.tool_fns[tool_name] = fn
            return fn

        return deco


EXPECTED_TOOLS = {
    # desktops
    "list_desktops", "get_current_desktop", "create_desktop", "delete_desktop",
    "switch_to_desktop", "rename_desktop", "pin_window_all_desktops",
    "unpin_window", "pin_app_all_desktops", "unpin_app", "is_pinned",
    # windows
    "list_windows", "move_window", "resize_window", "close_window",
    "focus_window", "relabel_window", "minimize_window", "maximize_window",
    "restore_window",
    # layouts / monitors
    "list_monitors", "list_layout_presets", "compute_layout", "apply_layout",
    # launchers
    "launch_chrome", "launch_edge", "launch_terminal", "launch_vscode", "launch_app",
    # adoption
    "list_unmanaged_windows", "adopt_window", "release_window",
    # query
    "find_window_by_title", "find_chrome_tab",
}


def _register_all() -> FakeMCP:
    from vdesktop_plugin.tools import adoption, desktops, layouts, query
    from vdesktop_plugin.tools import windows as window_ops
    from vdesktop_plugin.tools.launchers import register as register_launchers

    mcp = FakeMCP()
    desktops.register(mcp)
    layouts.register(mcp)
    window_ops.register(mcp)
    register_launchers(mcp)
    adoption.register(mcp)
    query.register(mcp)
    return mcp


def test_full_tool_surface_registers():
    mcp = _register_all()
    assert set(mcp.tool_names) == EXPECTED_TOOLS


def test_no_duplicate_tool_registrations():
    mcp = _register_all()
    assert len(mcp.tool_names) == len(set(mcp.tool_names))


def test_adopt_window_app_type_hint_is_literal():
    """Regression: app_type_hint must be Optional[Literal[...]] with exactly
    the five classifier values, not a plain Optional[str]."""
    mcp = _register_all()
    fn = mcp.tool_fns["adopt_window"]

    # get_type_hints resolves forward refs; include extras so Literal resolves.
    hints = typing.get_type_hints(fn, include_extras=True)
    annotation = hints["app_type_hint"]

    # Must be Optional[...], i.e. Union[..., None]
    outer_args = typing.get_args(annotation)
    assert type(None) in outer_args, (
        f"app_type_hint annotation {annotation!r} is not Optional (no NoneType)"
    )

    # Find the Literal inside the Optional union
    literal_type = next(
        (a for a in outer_args if typing.get_origin(a) is typing.Literal),
        None,
    )
    assert literal_type is not None, (
        f"app_type_hint annotation {annotation!r} contains no Literal type"
    )

    literal_values = set(typing.get_args(literal_type))
    expected_values = {"chrome", "edge", "vscode", "terminal", "unknown"}
    assert literal_values == expected_values, (
        f"Literal args {literal_values!r} != expected {expected_values!r}"
    )
