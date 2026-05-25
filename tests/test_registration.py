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


def test_launch_app_singleton_side_effect_warning():
    """Regression #23: launch_app docstring must warn that singleton apps can
    activate and relocate a pre-existing instance as a side-effect."""
    mcp = _register_all()
    doc = mcp.tool_fns["launch_app"].__doc__

    # Top-level warning: relocation side-effect mentioned
    assert "relocat" in doc.lower(), (
        "launch_app docstring missing top-level singleton relocation warning"
    )
    # Identification arg block: recovery guidance present
    assert "list_windows" in doc or "find_window_by_title" in doc, (
        "launch_app docstring missing recovery guidance in identification block"
    )


def test_list_windows_documents_unmanaged_shape():
    """Regression #31: list_windows docstring must document the complete unmanaged
    row shape (hwnd, pid, title, class_name, app_type, desktop_guid, bounds) and
    name which tracked-window fields are absent from those rows."""
    mcp = _register_all()
    doc = mcp.tool_fns["list_windows"].__doc__

    assert "unmanaged" in doc.lower(), (
        "list_windows docstring missing 'unmanaged' keyword"
    )
    # class_name must be listed as a present key
    assert "class_name" in doc, (
        "list_windows docstring must list 'class_name' as a key present in unmanaged rows"
    )
    # desktop_guid must be listed as PRESENT (not absent) in unmanaged rows
    assert "desktop_guid" in doc, (
        "list_windows docstring must mention 'desktop_guid' (present in unmanaged rows)"
    )
    assert "absent" in doc.lower() or "omit" in doc.lower(), (
        "list_windows docstring must state that tracked-window fields are absent "
        "from unmanaged rows"
    )


def test_compute_layout_documents_slot_naming():
    """Regression #31: compute_layout docstring must document both named (preset)
    and positional (columns/rows/grid) slot naming schemes with the correct grid
    format (compact rRcC, not row-N-col-N)."""
    mcp = _register_all()
    doc = mcp.tool_fns["compute_layout"].__doc__

    assert "col-" in doc, (
        "compute_layout docstring missing positional slot name example (col-)"
    )
    assert "preset" in doc.lower(), (
        "compute_layout docstring missing 'preset' slot naming reference"
    )
    assert "named" in doc.lower() or "positional" in doc.lower(), (
        "compute_layout docstring must contrast named vs positional slot names"
    )
    # Correct compact grid notation must be present
    assert "r0c0" in doc, (
        "compute_layout docstring must use the correct compact grid slot format 'r0c0'"
    )
    # Wrong verbose notation must NOT be present
    assert "row-0-col-0" not in doc, (
        "compute_layout docstring must not contain the incorrect 'row-0-col-0' grid format"
    )


def test_apply_layout_documents_slot_naming():
    """Regression #31: apply_layout docstring must document slot naming directly
    with the correct grid format (compact rRcC, not row-N-col-N)."""
    mcp = _register_all()
    doc = mcp.tool_fns["apply_layout"].__doc__

    assert "col-" in doc, (
        "apply_layout docstring missing positional slot name example (col-)"
    )
    assert "preset" in doc.lower(), (
        "apply_layout docstring missing 'preset' slot naming reference"
    )
    assert "named" in doc.lower() or "positional" in doc.lower(), (
        "apply_layout docstring must contrast named vs positional slot names"
    )
    # Correct compact grid notation must be present
    assert "r0c0" in doc, (
        "apply_layout docstring must use the correct compact grid slot format 'r0c0'"
    )
    # Wrong verbose notation must NOT be present
    assert "row-0-col-0" not in doc, (
        "apply_layout docstring must not contain the incorrect 'row-0-col-0' grid format"
    )


def test_create_desktop_documents_index_stability():
    """Regression #31: create_desktop docstring must document index instability
    and reference the correct 'guid' field (not 'desktop_guid')."""
    mcp = _register_all()
    doc = mcp.tool_fns["create_desktop"].__doc__

    assert "0-based" in doc, (
        "create_desktop docstring must mention '0-based' indexing"
    )
    assert (
        "unstable" in doc.lower()
        or "shift" in doc.lower()
        or "stable" in doc.lower()
    ), (
        "create_desktop docstring must note that indices/names shift and are unstable"
    )
    # The correct returned field name is "guid", not "desktop_guid"
    assert '"guid"' in doc, (
        "create_desktop docstring must reference the correct field name '\"guid\"'"
    )
    assert "desktop_guid" not in doc, (
        "create_desktop docstring must not use 'desktop_guid' — the actual key is 'guid'"
    )


def test_delete_desktop_documents_index_stability():
    """Regression #31: delete_desktop docstring must document index instability
    and reference the correct response keys ('deleted_guid' and 'guid', not 'desktop_guid')."""
    mcp = _register_all()
    doc = mcp.tool_fns["delete_desktop"].__doc__

    assert "0-based" in doc, (
        "delete_desktop docstring must mention '0-based' indexing"
    )
    assert (
        "unstable" in doc.lower()
        or "shift" in doc.lower()
        or "stable" in doc.lower()
    ), (
        "delete_desktop docstring must note that indices/names shift and are unstable"
    )
    # The response uses "deleted_guid" and remaining entries use "guid"
    assert "deleted_guid" in doc, (
        "delete_desktop docstring must reference the 'deleted_guid' response field"
    )
    assert '"guid"' in doc, (
        "delete_desktop docstring must reference the 'guid' field in remaining desktop entries"
    )
    # Must not use the wrong composite name
    assert "desktop_guid" not in doc, (
        "delete_desktop docstring must not use 'desktop_guid' — the actual keys are "
        "'deleted_guid' and 'guid'"
    )
