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

import inspect
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


def test_list_windows_default_includes_unmanaged():
    """Regression #36: list_windows must default include_unmanaged=True so agents
    see all top-level windows on a fresh session."""
    mcp = _register_all()
    fn = mcp.tool_fns["list_windows"]
    sig = inspect.signature(fn)
    default = sig.parameters["include_unmanaged"].default
    assert default is True, (
        f"list_windows include_unmanaged default is {default!r}, expected True"
    )


def test_list_windows_docstring_states_default_includes_unmanaged():
    """Regression #36: list_windows docstring must explain the new default and
    document the opt-out path (include_unmanaged=False)."""
    mcp = _register_all()
    doc = mcp.tool_fns["list_windows"].__doc__
    assert "default" in doc.lower(), (
        "list_windows docstring must mention 'default' to explain include_unmanaged=True"
    )
    assert "unmanaged" in doc.lower(), (
        "list_windows docstring must contain 'unmanaged'"
    )
    assert "include_unmanaged=False" in doc, (
        "list_windows docstring must document the opt-out path 'include_unmanaged=False'"
    )


def test_list_unmanaged_windows_docstring_references_list_windows():
    """Regression #36: list_unmanaged_windows docstring must reference list_windows
    so agents understand the relationship and preferred discovery path."""
    mcp = _register_all()
    doc = mcp.tool_fns["list_unmanaged_windows"].__doc__
    assert "list_windows" in doc, (
        "list_unmanaged_windows docstring must reference 'list_windows'"
    )


# ---------------------------------------------------------------------------
# Regression tests for ticket #39 — discovery and addressing friction
# ---------------------------------------------------------------------------

def test_find_chrome_tab_docstring_tab_index_minus_one_is_accessibility_signal():
    """Regression #39: find_chrome_tab docstring must explain that tab_index = -1
    signals that UIA/accessibility enumeration did not run."""
    mcp = _register_all()
    doc = mcp.tool_fns["find_chrome_tab"].__doc__

    assert "tab_index" in doc, (
        "find_chrome_tab docstring must mention 'tab_index'"
    )
    # Must reference accessibility or UIA near the -1 explanation
    doc_lower = doc.lower()
    assert "accessibility" in doc_lower or "uia" in doc_lower, (
        "find_chrome_tab docstring must reference 'accessibility' or 'UIA' when "
        "explaining the tab_index = -1 fallback"
    )
    assert "-1" in doc, (
        "find_chrome_tab docstring must contain '-1' as the fallback sentinel"
    )


def test_find_chrome_tab_docstring_empty_result_ambiguity_documented():
    """Regression #39: find_chrome_tab docstring must note that an empty result
    is ambiguous — not exclusively 'no match'."""
    mcp = _register_all()
    doc = mcp.tool_fns["find_chrome_tab"].__doc__

    doc_lower = doc.lower()
    # Must mention the no-Chrome-open possibility
    assert "no chrome" in doc_lower or "open" in doc_lower, (
        "find_chrome_tab docstring must note that no Chrome windows open is one "
        "possible cause of an empty result"
    )
    # Must note the cases are indistinguishable (the plan's exact word)
    assert "indistinguishable" in doc_lower or "ambiguous" in doc_lower, (
        "find_chrome_tab docstring must state that the empty-result causes are "
        "indistinguishable / ambiguous from the return value alone"
    )


def test_find_chrome_tab_adopted_flag_empty_result():
    """Regression: find_chrome_tab returns [] when manager returns no results;
    the adopted-flag injection loop must not raise on an empty list."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["find_chrome_tab"]

    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = []
    mock_manager.find_chrome_tab.return_value = []

    with patch("vdesktop_plugin.tools.query.MANAGER", mock_manager):
        result = fn(pattern="anything")

    assert result == [], f"Expected [], got {result!r}"


def test_find_chrome_tab_docstring_warns_mutation_at_top():
    """Regression: find_chrome_tab docstring must contain the mutation warning
    within the first ~200 characters so agents see it before truncation."""
    mcp = _register_all()
    doc = mcp.tool_fns["find_chrome_tab"].__doc__
    assert "WRITE" in doc[:200] or "ADOPT" in doc[:200].upper(), (
        "find_chrome_tab docstring must warn about the write/adoption side-effect "
        "near the top (first 200 chars)"
    )


def test_is_pinned_docstring_requires_tracked_window():
    """Regression #39: is_pinned docstring must explain it requires a handle_id
    that belongs to a tracked window."""
    mcp = _register_all()
    doc = mcp.tool_fns["is_pinned"].__doc__

    assert "tracked" in doc, (
        "is_pinned docstring must contain 'tracked'"
    )
    assert "handle_id" in doc, (
        "is_pinned docstring must contain 'handle_id'"
    )


def test_is_pinned_docstring_guides_to_list_windows_for_tracked_rows():
    """Regression #39: is_pinned docstring must mention list_windows as a
    source of pin state for already-tracked windows."""
    mcp = _register_all()
    doc = mcp.tool_fns["is_pinned"].__doc__

    assert "list_windows" in doc, (
        "is_pinned docstring must reference 'list_windows' — tracked rows "
        "already include is_pinned and is_app_pinned"
    )


def test_is_pinned_docstring_guides_to_adopt_window_for_untracked():
    """Regression #39: is_pinned docstring must guide agents to adopt_window
    when the window is not yet tracked."""
    mcp = _register_all()
    doc = mcp.tool_fns["is_pinned"].__doc__

    assert "adopt_window" in doc, (
        "is_pinned docstring must reference 'adopt_window' for untracked windows"
    )


def test_switch_to_desktop_docstring_documents_target_forms():
    """Regression #39: switch_to_desktop docstring must document that target
    accepts an index, a name, and a GUID."""
    mcp = _register_all()
    doc = mcp.tool_fns["switch_to_desktop"].__doc__

    assert "index" in doc.lower(), (
        "switch_to_desktop docstring must document 'index' as a target form"
    )
    assert "name" in doc.lower(), (
        "switch_to_desktop docstring must document 'name' as a target form"
    )
    assert "guid" in doc.lower(), (
        "switch_to_desktop docstring must document 'GUID' as a target form"
    )


def test_rename_desktop_docstring_documents_target_forms():
    """Regression #39: rename_desktop docstring must document that target
    accepts an index, a name, and a GUID."""
    mcp = _register_all()
    doc = mcp.tool_fns["rename_desktop"].__doc__

    assert "index" in doc.lower(), (
        "rename_desktop docstring must document 'index' as a target form"
    )
    assert "name" in doc.lower(), (
        "rename_desktop docstring must document 'name' as a target form"
    )
    assert "guid" in doc.lower(), (
        "rename_desktop docstring must document 'GUID' as a target form"
    )


def test_switch_to_desktop_docstring_warns_guid_quoting():
    """Regression #39: switch_to_desktop docstring must warn that a GUID must
    not be wrapped in extra quotes."""
    mcp = _register_all()
    doc = mcp.tool_fns["switch_to_desktop"].__doc__

    assert "quote" in doc.lower() or "quoted" in doc.lower(), (
        "switch_to_desktop docstring must warn about double-quoting a GUID "
        "('quote' or 'quoted')"
    )


def test_rename_desktop_docstring_warns_guid_quoting():
    """Regression #39: rename_desktop docstring must warn that a GUID must
    not be wrapped in extra quotes."""
    mcp = _register_all()
    doc = mcp.tool_fns["rename_desktop"].__doc__

    assert "quote" in doc.lower() or "quoted" in doc.lower(), (
        "rename_desktop docstring must warn about double-quoting a GUID "
        "('quote' or 'quoted')"
    )


def test_find_window_by_title_docstring_documents_handle_id_null():
    """Regression #39: find_window_by_title docstring must note that handle_id
    is null/None for untracked windows."""
    mcp = _register_all()
    doc = mcp.tool_fns["find_window_by_title"].__doc__

    assert "null" in doc.lower() or "none" in doc.lower(), (
        "find_window_by_title docstring must state that handle_id is null/None "
        "for untracked windows"
    )
    assert "handle_id" in doc, (
        "find_window_by_title docstring must mention 'handle_id'"
    )


def test_find_window_by_title_docstring_distinguishes_hwnd_from_handle_id():
    """Regression #39: find_window_by_title docstring must distinguish hwnd
    (always present) from handle_id (registry key, only for tracked windows)
    and point to adopt_window."""
    mcp = _register_all()
    doc = mcp.tool_fns["find_window_by_title"].__doc__

    assert "hwnd" in doc, (
        "find_window_by_title docstring must mention 'hwnd'"
    )
    assert "handle_id" in doc, (
        "find_window_by_title docstring must mention 'handle_id'"
    )
    assert "adopt_window" in doc, (
        "find_window_by_title docstring must reference 'adopt_window' for "
        "obtaining a handle_id"
    )
