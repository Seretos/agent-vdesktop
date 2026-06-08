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
    """Regression #39/#49: switch_to_desktop docstring must guide callers to
    use the braced GUID form returned by list_desktops."""
    mcp = _register_all()
    doc = mcp.tool_fns["switch_to_desktop"].__doc__

    assert "braces" in doc.lower() or "curly" in doc.lower() or "{" in doc, (
        "switch_to_desktop docstring must reference braces/curly braces or "
        "show a braced GUID example ('{' character)"
    )


def test_rename_desktop_docstring_warns_guid_quoting():
    """Regression #39/#49: rename_desktop docstring must guide callers to
    use the braced GUID form returned by list_desktops."""
    mcp = _register_all()
    doc = mcp.tool_fns["rename_desktop"].__doc__

    assert "braces" in doc.lower() or "curly" in doc.lower() or "{" in doc, (
        "rename_desktop docstring must reference braces/curly braces or "
        "show a braced GUID example ('{' character)"
    )


# ---------------------------------------------------------------------------
# Regression tests for ticket #50 — tool surface clarity
# ---------------------------------------------------------------------------

def test_rename_desktop_unknown_name_reraises_with_list_desktops_hint():
    """Regression #50: rename_desktop enriches 'Unknown desktop reference'
    error with the desktop count and a hint to call list_desktops()."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["rename_desktop"]

    mock_manager = MagicMock()
    mock_manager.rename_desktop.side_effect = ValueError("Unknown desktop reference: 'foo'")
    mock_manager.list_desktops.return_value = [{"guid": "a"}, {"guid": "b"}]

    with patch("vdesktop_plugin.tools.desktops.MANAGER", mock_manager):
        try:
            fn(target="foo", new_name="Bar")
            assert False, "Expected ValueError to be raised"
        except ValueError as exc:
            msg = str(exc)
            assert "list_desktops" in msg, (
                f"Error message must mention 'list_desktops': {msg!r}"
            )
            assert "2" in msg, (
                f"Error message must include the desktop count '2': {msg!r}"
            )


def test_is_pinned_returns_renamed_keys():
    """Regression #50: is_pinned tool must expose keys is_pinned/is_app_pinned
    (aligned with list_windows rows), NOT window_pinned/app_pinned."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["is_pinned"]

    mock_manager = MagicMock()
    mock_manager.is_pinned.return_value = {
        "handle_id": "h1",
        "window_pinned": True,
        "app_pinned": False,
    }

    with patch("vdesktop_plugin.tools.desktops.MANAGER", mock_manager):
        result = fn(handle_id="h1")

    assert "is_pinned" in result, (
        f"is_pinned result must have key 'is_pinned', got keys: {list(result.keys())}"
    )
    assert "is_app_pinned" in result, (
        f"is_pinned result must have key 'is_app_pinned', got keys: {list(result.keys())}"
    )
    assert "window_pinned" not in result, (
        "is_pinned result must NOT expose raw key 'window_pinned'"
    )
    assert "app_pinned" not in result, (
        "is_pinned result must NOT expose raw key 'app_pinned'"
    )
    assert result["is_pinned"] is True
    assert result["is_app_pinned"] is False
    assert result["handle_id"] == "h1", "passthrough fields must be preserved"


def test_release_window_raises_on_released_false():
    """Regression #50: release_window raises ValueError when MANAGER returns
    {released: False} (unknown or already-released handle)."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["release_window"]

    mock_manager = MagicMock()
    mock_manager.release_window.return_value = {"released": False}

    with patch("vdesktop_plugin.tools.adoption.MANAGER", mock_manager):
        try:
            fn(handle_id="h-unknown")
            assert False, "Expected ValueError to be raised"
        except ValueError as exc:
            msg = str(exc)
            assert "list_windows" in msg, (
                f"Error message must mention 'list_windows': {msg!r}"
            )


def test_release_window_returns_dict_on_success():
    """Regression #50: release_window returns the result dict when
    MANAGER returns {released: True}."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["release_window"]

    mock_manager = MagicMock()
    mock_manager.release_window.return_value = {"released": True, "handle_id": "h1"}

    with patch("vdesktop_plugin.tools.adoption.MANAGER", mock_manager):
        result = fn(handle_id="h1")

    assert result == {"released": True, "handle_id": "h1"}, (
        f"release_window must return the dict unchanged on success, got: {result!r}"
    )


def test_compute_layout_raises_valueerror_for_string_spec():
    """Regression #50: compute_layout raises ValueError (not a raw pydantic
    error) when called with a plain string as spec."""
    mcp = _register_all()
    fn = mcp.tool_fns["compute_layout"]

    try:
        fn(spec="three-columns")
        assert False, "Expected ValueError to be raised for a string spec"
    except ValueError as exc:
        msg = str(exc)
        assert "preset" in msg.lower() or '{"type"' in msg, (
            f"ValueError message must guide toward the preset dict form: {msg!r}"
        )
        assert "list_layout_presets" in msg, (
            f"ValueError message must mention 'list_layout_presets': {msg!r}"
        )
    except Exception as exc:
        assert False, (
            f"compute_layout must raise ValueError for string spec, got {type(exc).__name__}: {exc}"
        )


def test_pin_window_all_desktops_already_pinned_sanity():
    """Regression #50 sanity: pin_window_all_desktops still injects already_pinned
    correctly after #50 changes (is_pinned pre-check still reads window_pinned from
    MANAGER directly, not from the tool wrapper)."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["pin_window_all_desktops"]

    mock_manager = MagicMock()
    mock_manager.is_pinned.return_value = {
        "handle_id": "h1",
        "window_pinned": False,
        "app_pinned": False,
    }
    mock_manager.pin_window_all_desktops.return_value = {
        "handle_id": "h1",
        "window_pinned": True,
    }

    with patch("vdesktop_plugin.tools.desktops.MANAGER", mock_manager):
        result = fn(handle_id="h1")

    assert "already_pinned" in result, (
        "pin_window_all_desktops result must include 'already_pinned'"
    )
    assert result["already_pinned"] is False, (
        f"already_pinned must be False when window was not pinned before the call"
    )


# --- Docstring assertion tests for ticket #50 ---

def test_create_desktop_docstring_mentions_active_desktop_not_changed():
    """Regression #50: create_desktop docstring must state that the active
    (foreground) desktop is NOT changed."""
    mcp = _register_all()
    doc = mcp.tool_fns["create_desktop"].__doc__

    doc_lower = doc.lower()
    assert "active" in doc_lower or "foreground" in doc_lower, (
        "create_desktop docstring must mention 'active' or 'foreground' desktop"
    )
    assert "not" in doc_lower, (
        "create_desktop docstring must state the active desktop is NOT changed"
    )


def test_delete_desktop_docstring_mentions_lower_index_fallback():
    """Regression #50: delete_desktop docstring must clarify the fallback as
    the lower-index neighbouring desktop."""
    mcp = _register_all()
    doc = mcp.tool_fns["delete_desktop"].__doc__

    assert "index" in doc.lower(), (
        "delete_desktop docstring must mention 'index' when describing the fallback"
    )
    assert "left" in doc.lower() or "lower" in doc.lower(), (
        "delete_desktop docstring must mention 'left' or 'lower' for the fallback desktop"
    )


def test_resize_window_docstring_mentions_slot_and_desktop():
    """Regression #50: resize_window docstring must mention 'slot' and 'desktop'
    to guide callers toward move_window for those use cases."""
    mcp = _register_all()
    doc = mcp.tool_fns["resize_window"].__doc__

    assert "slot" in doc, (
        "resize_window docstring must mention 'slot' (to guide toward move_window)"
    )
    assert "desktop" in doc.lower(), (
        "resize_window docstring must mention 'desktop' (to guide toward move_window)"
    )


def test_list_windows_docstring_mentions_minimized_sentinel_bounds():
    """Regression #50: list_windows docstring must warn that minimized window
    bounds are OS sentinel coordinates (near -32000) and not meaningful."""
    mcp = _register_all()
    doc = mcp.tool_fns["list_windows"].__doc__

    assert "minimized" in doc.lower(), (
        "list_windows docstring must mention 'minimized'"
    )
    assert "-32000" in doc or "sentinel" in doc.lower(), (
        "list_windows docstring must mention '-32000' or 'sentinel' for minimized bounds"
    )


def test_find_window_by_title_empty_pattern_matches_all():
    """Regression #50: find_window_by_title docstring must document that
    pattern='' matches ALL visible windows."""
    mcp = _register_all()
    doc = mcp.tool_fns["find_window_by_title"].__doc__

    doc_lower = doc.lower()
    assert 'pattern=""' in doc or "empty" in doc_lower, (
        'find_window_by_title docstring must document that pattern="" matches all windows'
    )
    assert "all" in doc_lower, (
        "find_window_by_title docstring must mention 'all' (empty pattern matches all)"
    )


def test_compute_layout_docstring_preset_dict_form_and_list_layout_presets():
    """Regression #50: compute_layout docstring must show the preset dict form
    {'type': 'preset', ...} and reference list_layout_presets()."""
    mcp = _register_all()
    doc = mcp.tool_fns["compute_layout"].__doc__

    assert '{"type": "preset"' in doc or "\"type\": \"preset\"" in doc, (
        'compute_layout docstring must show the {"type": "preset", ...} form'
    )
    assert "list_layout_presets" in doc, (
        "compute_layout docstring must reference 'list_layout_presets'"
    )


def test_compute_layout_docstring_preview_vs_apply_layout_contrast():
    """Regression #50: compute_layout docstring must contrast it with
    apply_layout (preview-only vs persists active layout)."""
    mcp = _register_all()
    doc = mcp.tool_fns["compute_layout"].__doc__

    doc_lower = doc.lower()
    assert "preview" in doc_lower or "side effect" in doc_lower or "no side" in doc_lower, (
        "compute_layout docstring must describe it as preview-only / no side effects"
    )
    assert "apply_layout" in doc, (
        "compute_layout docstring must reference 'apply_layout'"
    )


def test_apply_layout_docstring_mentions_active_layout_and_move_window():
    """Regression #50: apply_layout docstring must state it sets the active
    layout and mention move_window as a tool that can target slot ids."""
    mcp = _register_all()
    doc = mcp.tool_fns["apply_layout"].__doc__

    doc_lower = doc.lower()
    assert "active" in doc_lower, (
        "apply_layout docstring must mention 'active' layout"
    )
    assert "move_window" in doc, (
        "apply_layout docstring must reference 'move_window'"
    )


def test_is_pinned_docstring_mentions_renamed_keys():
    """Regression #50: is_pinned docstring must document that returned keys are
    is_pinned / is_app_pinned (aligned with list_windows rows)."""
    mcp = _register_all()
    doc = mcp.tool_fns["is_pinned"].__doc__

    assert "is_pinned" in doc, (
        "is_pinned docstring must mention 'is_pinned' as a returned key"
    )
    assert "is_app_pinned" in doc, (
        "is_pinned docstring must mention 'is_app_pinned' as a returned key"
    )
    assert "list_windows" in doc, (
        "is_pinned docstring must reference alignment with 'list_windows' rows"
    )


def test_pin_window_all_desktops_docstring_mentions_already_pinned():
    """Regression #50: pin_window_all_desktops docstring must document the
    already_pinned field in the returned dict."""
    mcp = _register_all()
    doc = mcp.tool_fns["pin_window_all_desktops"].__doc__

    assert "already_pinned" in doc, (
        "pin_window_all_desktops docstring must mention 'already_pinned'"
    )


def test_release_window_docstring_mentions_raises_on_unknown():
    """Regression #50: release_window docstring must state it raises when
    handle_id is not a currently-tracked window."""
    mcp = _register_all()
    doc = mcp.tool_fns["release_window"].__doc__

    doc_lower = doc.lower()
    assert "raises" in doc_lower or "raise" in doc_lower, (
        "release_window docstring must mention that it raises on unknown handle"
    )
    assert "list_windows" in doc, (
        "release_window docstring must reference 'list_windows'"
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


# ---------------------------------------------------------------------------
# Regression tests for ticket #40 — return shape / error message polish
# ---------------------------------------------------------------------------

def test_move_window_slot_error_mentions_available_slots():
    """Regression #40: move_window wraps KeyError from lib into ValueError with
    a message that references slots and lists guidance tools."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["move_window"]

    mock_manager = MagicMock()
    mock_manager.move_window.side_effect = KeyError("Slot 'bad' unknown — apply_layout first")

    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        try:
            fn(handle_id="h1", target={"slot": "bad"})
            assert False, "Expected ValueError to be raised"
        except ValueError as exc:
            msg = str(exc)
            assert "slot" in msg.lower(), f"Error message must mention 'slot': {msg!r}"
            assert "apply_layout" in msg or "list_layout_presets" in msg, (
                f"Error message must mention apply_layout or list_layout_presets: {msg!r}"
            )


def test_move_window_untracked_handle_keyerror_propagates_unchanged():
    """Regression #40 fix: a KeyError raised by REGISTRY.require (untracked handle_id)
    must NOT be converted to ValueError even when target contains 'slot'.
    The guard must inspect the exception message, not only the target dict."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["move_window"]

    mock_manager = MagicMock()
    mock_manager.move_window.side_effect = KeyError("No tracked window for handle/label 'h-bad'")

    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        try:
            fn(handle_id="h-bad", target={"slot": "x"})
            assert False, "Expected KeyError to be raised"
        except KeyError:
            pass  # correct — original KeyError must propagate unchanged
        except ValueError as exc:
            assert False, (
                f"untracked-handle KeyError must not be converted to ValueError: {exc}"
            )


def test_switch_to_desktop_unknown_name_error_mentions_count():
    """Regression #40: switch_to_desktop enriches 'Unknown desktop reference'
    error with the desktop count."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["switch_to_desktop"]

    mock_manager = MagicMock()
    mock_manager.switch_to_desktop.side_effect = ValueError("Unknown desktop reference: 'foo'")
    mock_manager.list_desktops.return_value = [{"guid": "a"}, {"guid": "b"}, {"guid": "c"}]

    with patch("vdesktop_plugin.tools.desktops.MANAGER", mock_manager):
        try:
            fn(target="foo")
            assert False, "Expected ValueError to be raised"
        except ValueError as exc:
            msg = str(exc)
            assert "3" in msg, f"Error message must mention count '3': {msg!r}"


def test_delete_desktop_docstring_documents_last_desktop_guard():
    """Regression #40: delete_desktop docstring must mention last/only desktop
    behaviour."""
    mcp = _register_all()
    doc = mcp.tool_fns["delete_desktop"].__doc__

    assert "last" in doc.lower() or "only" in doc.lower(), (
        "delete_desktop docstring must mention 'last' or 'only' desktop guard"
    )


def test_delete_desktop_docstring_documents_target_forms():
    """Regression #40: delete_desktop docstring must document index, name, and
    GUID forms for the target parameter."""
    mcp = _register_all()
    doc = mcp.tool_fns["delete_desktop"].__doc__

    assert "index" in doc.lower(), (
        "delete_desktop docstring must document 'index' as a target form"
    )
    assert "name" in doc.lower(), (
        "delete_desktop docstring must document 'name' as a target form"
    )
    assert "guid" in doc.lower(), (
        "delete_desktop docstring must document 'guid' as a target form"
    )


def test_adopt_window_return_includes_slot_id():
    """Regression #40: adopt_window result (fresh adoption) must include slot_id=None."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["adopt_window"]

    mock_manager = MagicMock()
    mock_manager.adopt_window.return_value = {
        "handle_id": "h1",
        "hwnd": 1,
        "pid": 123,
        "label": None,
        "app_type": "unknown",
        "desktop_guid": "guid-1",
        "bounds": {"x": 0, "y": 0, "w": 100, "h": 100},
        "title": "Test Window",
    }

    with patch("vdesktop_plugin.tools.adoption.MANAGER", mock_manager):
        result = fn(hwnd=1)

    assert "slot_id" in result, "adopt_window result must include 'slot_id' key"
    assert result["slot_id"] is None, (
        f"adopt_window fresh adoption result must have slot_id=None, got {result['slot_id']!r}"
    )


def test_adopt_window_already_tracked_return_includes_slot_id():
    """Regression #40: adopt_window result (already-tracked path) must include slot_id=None."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["adopt_window"]

    mock_manager = MagicMock()
    mock_manager.adopt_window.return_value = {
        "handle_id": "h1",
        "already_tracked": True,
    }

    with patch("vdesktop_plugin.tools.adoption.MANAGER", mock_manager):
        result = fn(hwnd=1)

    assert "slot_id" in result, "adopt_window already-tracked result must include 'slot_id' key"
    assert result["slot_id"] is None, (
        f"adopt_window already-tracked result must have slot_id=None, got {result['slot_id']!r}"
    )


def test_pin_window_all_desktops_return_includes_already_pinned_false():
    """Regression #40: pin_window_all_desktops returns already_pinned=False when
    the window was not pinned before the call."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["pin_window_all_desktops"]

    mock_manager = MagicMock()
    mock_manager.is_pinned.return_value = {
        "handle_id": "h1",
        "window_pinned": False,
        "app_pinned": False,
    }
    mock_manager.pin_window_all_desktops.return_value = {
        "handle_id": "h1",
        "window_pinned": True,
    }

    with patch("vdesktop_plugin.tools.desktops.MANAGER", mock_manager):
        result = fn(handle_id="h1")

    assert "already_pinned" in result, (
        "pin_window_all_desktops result must include 'already_pinned' key"
    )
    assert result["already_pinned"] is False, (
        f"already_pinned must be False when window was not pinned: {result['already_pinned']!r}"
    )


def test_pin_window_all_desktops_return_includes_already_pinned_true():
    """Regression #40: pin_window_all_desktops returns already_pinned=True when
    the window was already pinned before the call."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["pin_window_all_desktops"]

    mock_manager = MagicMock()
    mock_manager.is_pinned.return_value = {
        "handle_id": "h1",
        "window_pinned": True,
        "app_pinned": False,
    }
    mock_manager.pin_window_all_desktops.return_value = {
        "handle_id": "h1",
        "window_pinned": True,
    }

    with patch("vdesktop_plugin.tools.desktops.MANAGER", mock_manager):
        result = fn(handle_id="h1")

    assert "already_pinned" in result, (
        "pin_window_all_desktops result must include 'already_pinned' key"
    )
    assert result["already_pinned"] is True, (
        f"already_pinned must be True when window was already pinned: {result['already_pinned']!r}"
    )


def test_list_layout_presets_includes_slots():
    """Regression #40: list_layout_presets must include a non-empty 'slots' list
    for each preset."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["list_layout_presets"]

    mock_manager = MagicMock()
    mock_manager.list_layout_presets.return_value = [
        {"name": "two-columns", "description": "50/50 vertical split"},
        {"name": "three-columns", "description": "33/33/33 vertical split"},
        {"name": "fullscreen", "description": "single window covers the entire work area"},
    ]

    with patch("vdesktop_plugin.tools.layouts.MANAGER", mock_manager):
        result = fn()

    for preset in result:
        assert "slots" in preset, (
            f"list_layout_presets result for {preset.get('name')!r} must include 'slots' key"
        )
        assert len(preset["slots"]) > 0, (
            f"list_layout_presets slots for {preset.get('name')!r} must be non-empty"
        )


def test_list_monitors_docstring_names_win32_path():
    """Regression #40: list_monitors docstring must reference the Win32 device
    path nature of 'name' and mention 'index'."""
    mcp = _register_all()
    doc = mcp.tool_fns["list_monitors"].__doc__

    assert "index" in doc.lower(), (
        "list_monitors docstring must mention 'index'"
    )
    # Must reference the Win32 / device-path nature of 'name'
    assert "win32" in doc.lower() or "device" in doc.lower() or "DISPLAY" in doc, (
        "list_monitors docstring must describe 'name' as a Win32 device path"
    )


def test_move_window_docstring_notes_bounds_overlap_with_resize_window():
    """Regression #40: move_window docstring must reference resize_window to
    explain the bounds overlap."""
    mcp = _register_all()
    doc = mcp.tool_fns["move_window"].__doc__

    assert "resize_window" in doc, (
        "move_window docstring must mention 'resize_window'"
    )


def test_resize_window_docstring_notes_overlap_with_move_window():
    """Regression #40: resize_window docstring must reference move_window to
    explain the overlap."""
    mcp = _register_all()
    doc = mcp.tool_fns["resize_window"].__doc__

    assert "move_window" in doc, (
        "resize_window docstring must mention 'move_window'"
    )


# ---------------------------------------------------------------------------
# Regression tests for ticket #49 — GUID braced-form docstring corrections
# ---------------------------------------------------------------------------

def test_delete_desktop_docstring_guid_requires_braced_form():
    """Regression #49: delete_desktop docstring must show a braced GUID example
    and must not contain the old misleading 'bare UUID' or 'without extra quotes'
    language."""
    mcp = _register_all()
    doc = mcp.tool_fns["delete_desktop"].__doc__

    # (a) A braced-form example must be present (the '{' character appears in
    #     the GUID bullet, e.g. ``"{3f7b2e1a-...}"``).
    assert "{" in doc, (
        "delete_desktop docstring GUID bullet must contain a braced example "
        "('{' character) as returned by list_desktops"
    )
    # (b) The old incorrect 'bare UUID' phrasing must be gone.
    assert "bare UUID" not in doc, (
        "delete_desktop docstring must not contain 'bare UUID' — "
        "callers need the braced form, not a bare UUID"
    )
    # (c) The old misleading 'without extra quotes' phrasing must be gone.
    assert "without extra quotes" not in doc, (
        "delete_desktop docstring must not contain 'without extra quotes' — "
        "the issue is missing curly braces, not extra quote characters"
    )


def test_switch_to_desktop_docstring_guid_requires_braced_form():
    """Regression #49: switch_to_desktop docstring must show a braced GUID
    example and must not contain the old misleading 'bare UUID' or 'without
    extra quotes' language."""
    mcp = _register_all()
    doc = mcp.tool_fns["switch_to_desktop"].__doc__

    # (a) A braced-form example must be present.
    assert "{" in doc, (
        "switch_to_desktop docstring GUID bullet must contain a braced example "
        "('{' character) as returned by list_desktops"
    )
    # (b) The old incorrect 'bare UUID' phrasing must be gone.
    assert "bare UUID" not in doc, (
        "switch_to_desktop docstring must not contain 'bare UUID' — "
        "callers need the braced form, not a bare UUID"
    )
    # (c) The old misleading 'without extra quotes' phrasing must be gone.
    assert "without extra quotes" not in doc, (
        "switch_to_desktop docstring must not contain 'without extra quotes' — "
        "the issue is missing curly braces, not extra quote characters"
    )


def test_rename_desktop_docstring_guid_requires_braced_form():
    """Regression #49: rename_desktop docstring must show a braced GUID example
    and must not contain the old misleading 'bare UUID' or 'without extra
    quotes' language."""
    mcp = _register_all()
    doc = mcp.tool_fns["rename_desktop"].__doc__

    # (a) A braced-form example must be present.
    assert "{" in doc, (
        "rename_desktop docstring GUID bullet must contain a braced example "
        "('{' character) as returned by list_desktops"
    )
    # (b) The old incorrect 'bare UUID' phrasing must be gone.
    assert "bare UUID" not in doc, (
        "rename_desktop docstring must not contain 'bare UUID' — "
        "callers need the braced form, not a bare UUID"
    )
    # (c) The old misleading 'without extra quotes' phrasing must be gone.
    assert "without extra quotes" not in doc, (
        "rename_desktop docstring must not contain 'without extra quotes' — "
        "the issue is missing curly braces, not extra quote characters"
    )


# ---------------------------------------------------------------------------
# Regression tests for ticket #59 — expose env parameter on launcher tools
# ---------------------------------------------------------------------------

def test_launch_app_has_env_parameter_defaulting_to_none():
    """Regression #59: launch_app tool function must have an `env` parameter
    with a default of None."""
    mcp = _register_all()
    fn = mcp.tool_fns["launch_app"]
    sig = inspect.signature(fn)
    assert "env" in sig.parameters, (
        "launch_app signature must include an 'env' parameter"
    )
    assert sig.parameters["env"].default is None, (
        f"launch_app 'env' parameter default must be None, "
        f"got {sig.parameters['env'].default!r}"
    )


def test_launch_chrome_has_env_parameter_defaulting_to_none():
    """Regression #59: launch_chrome tool function must have an `env` parameter
    with a default of None."""
    mcp = _register_all()
    fn = mcp.tool_fns["launch_chrome"]
    sig = inspect.signature(fn)
    assert "env" in sig.parameters, (
        "launch_chrome signature must include an 'env' parameter"
    )
    assert sig.parameters["env"].default is None, (
        f"launch_chrome 'env' parameter default must be None, "
        f"got {sig.parameters['env'].default!r}"
    )


def test_launch_edge_has_env_parameter_defaulting_to_none():
    """Regression #59: launch_edge tool function must have an `env` parameter
    with a default of None."""
    mcp = _register_all()
    fn = mcp.tool_fns["launch_edge"]
    sig = inspect.signature(fn)
    assert "env" in sig.parameters, (
        "launch_edge signature must include an 'env' parameter"
    )
    assert sig.parameters["env"].default is None, (
        f"launch_edge 'env' parameter default must be None, "
        f"got {sig.parameters['env'].default!r}"
    )


def test_launch_terminal_has_env_parameter_defaulting_to_none():
    """Regression #59: launch_terminal tool function must have an `env` parameter
    with a default of None."""
    mcp = _register_all()
    fn = mcp.tool_fns["launch_terminal"]
    sig = inspect.signature(fn)
    assert "env" in sig.parameters, (
        "launch_terminal signature must include an 'env' parameter"
    )
    assert sig.parameters["env"].default is None, (
        f"launch_terminal 'env' parameter default must be None, "
        f"got {sig.parameters['env'].default!r}"
    )


def test_launch_vscode_has_env_parameter_defaulting_to_none():
    """Regression #59: launch_vscode tool function must have an `env` parameter
    with a default of None."""
    mcp = _register_all()
    fn = mcp.tool_fns["launch_vscode"]
    sig = inspect.signature(fn)
    assert "env" in sig.parameters, (
        "launch_vscode signature must include an 'env' parameter"
    )
    assert sig.parameters["env"].default is None, (
        f"launch_vscode 'env' parameter default must be None, "
        f"got {sig.parameters['env'].default!r}"
    )


def test_launch_app_forwards_env_to_manager():
    """Regression #59: launch_app must forward the env kwarg to MANAGER.launch_app
    as a keyword argument."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["launch_app"]

    mock_manager = MagicMock()
    mock_manager.launch_app.return_value = {"handle_id": "h1"}

    with patch("vdesktop_plugin.tools.launchers.generic.MANAGER", mock_manager):
        result = fn(executable="notepad.exe", env={"MY_VAR": "val"})

    mock_manager.launch_app.assert_called_once()
    _, kwargs = mock_manager.launch_app.call_args
    assert kwargs.get("env") == {"MY_VAR": "val"}, (
        f"MANAGER.launch_app must be called with env={{'MY_VAR': 'val'}}, "
        f"got call_args={mock_manager.launch_app.call_args!r}"
    )


def test_launch_app_docstring_describes_env_inherit_and_overlay():
    """Regression #59: launch_app docstring must describe the env parameter
    with inherit-and-overlay semantics."""
    mcp = _register_all()
    doc = mcp.tool_fns["launch_app"].__doc__

    assert "env" in doc, (
        "launch_app docstring must mention 'env' parameter"
    )
    doc_lower = doc.lower()
    assert "inherit" in doc_lower or "overlay" in doc_lower or "overlaid" in doc_lower, (
        "launch_app docstring must describe inherit/overlay semantics for env"
    )


# ---------------------------------------------------------------------------
# Regression tests for ticket #63 — expose wsl_distro on launch_vscode
# ---------------------------------------------------------------------------

def test_launch_vscode_has_wsl_distro_parameter_defaulting_to_none():
    """Regression #63: launch_vscode tool function must have a `wsl_distro`
    parameter with a default of None."""
    mcp = _register_all()
    fn = mcp.tool_fns["launch_vscode"]
    sig = inspect.signature(fn)
    assert "wsl_distro" in sig.parameters, (
        "launch_vscode signature must include a 'wsl_distro' parameter"
    )
    assert sig.parameters["wsl_distro"].default is None, (
        f"launch_vscode 'wsl_distro' parameter default must be None, "
        f"got {sig.parameters['wsl_distro'].default!r}"
    )


def test_launch_vscode_forwards_wsl_distro_to_manager():
    """Regression #63: launch_vscode must forward the wsl_distro kwarg to
    MANAGER.launch_vscode as a keyword argument."""
    from unittest.mock import MagicMock, patch

    mcp = _register_all()
    fn = mcp.tool_fns["launch_vscode"]

    mock_manager = MagicMock()
    mock_manager.launch_vscode.return_value = {"handle_id": "h1"}

    with patch("vdesktop_plugin.tools.launchers.vscode.MANAGER", mock_manager):
        result = fn(folder="/home/user/project", wsl_distro="claude-agents")

    mock_manager.launch_vscode.assert_called_once()
    _, kwargs = mock_manager.launch_vscode.call_args
    assert kwargs.get("wsl_distro") == "claude-agents", (
        f"MANAGER.launch_vscode must be called with wsl_distro='claude-agents', "
        f"got call_args={mock_manager.launch_vscode.call_args!r}"
    )


def test_launch_vscode_docstring_mentions_wsl_distro():
    """Regression #63: launch_vscode docstring must mention 'wsl_distro'."""
    mcp = _register_all()
    doc = mcp.tool_fns["launch_vscode"].__doc__

    assert "wsl_distro" in doc, (
        "launch_vscode docstring must mention 'wsl_distro'"
    )
