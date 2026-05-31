"""MCP tools for monitors and layout computation. Thin wrappers over
lib_python_vdesktop.VDesktopManager."""
from __future__ import annotations

from typing import Optional, Union

from lib_python_vdesktop import LayoutSpec
from lib_python_vdesktop.layouts import PRESETS
from pydantic import ValidationError

from ._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool(name="list_monitors")
    def _list_monitors() -> list[dict]:
        """List all physical monitors with their bounds, work area, DPI, and primary flag.

        Each entry contains:
          - ``index``: 0-based integer. The primary monitor is always index 0.
            Use this value in layout specs (e.g. ``{"type": "preset", "monitor": 0}``).
          - ``name``: raw Win32 device path (e.g. ``\\\\.\\DISPLAY1``). This is an
            opaque OS identifier, not intended for display to users.
          - ``bounds``, ``work_area``, ``dpi``, ``primary``: geometry and display info.
        """
        return MANAGER.list_monitors()

    @mcp.tool()
    def list_layout_presets() -> list[dict]:
        """List built-in layout preset names with a short description and slot ids.

        Each entry contains:
          - ``name``: the preset name to pass to apply_layout / compute_layout.
          - ``description``: a human-readable summary of the layout.
          - ``slots``: list of slot_id strings available in this preset. These are
            the values you can pass as ``"slot"`` in move_window or launch_*.
        """
        presets = MANAGER.list_layout_presets()
        for preset in presets:
            name = preset.get("name", "")
            if name in PRESETS:
                preset["slots"] = [s["slot_id"] for s in PRESETS[name]()]
            else:
                preset["slots"] = []
        return presets

    @mcp.tool()
    def compute_layout(spec: LayoutSpec) -> list[dict]:
        """Resolve a LayoutSpec into concrete slot rectangles WITHOUT moving any
        windows. PREVIEW-ONLY — this call has no side effects and does NOT set
        the active layout. Use ``apply_layout`` to persist the layout so that
        slot ids can be targeted by ``move_window`` / ``launch_*``.

        PRESET INDIRECTION: to use a preset, pass
        ``{"type": "preset", "name": "<name>"}`` — a bare preset-name string
        is NOT accepted. Call ``list_layout_presets()`` to see valid names.

        A LayoutSpec is either ONE dict for one monitor, or a LIST of such
        dicts (one per monitor). Each dict must have a "type" key:

          {"type": "preset",  "name": "three-columns", "monitor": 0}
          {"type": "columns", "splits": [25, 50, 25],  "monitor": 0}
          {"type": "rows",    "splits": [50, 50],      "monitor": 0}
          {"type": "grid",    "cols": 2, "rows": 2,    "monitor": 0}
          {"type": "regions", "monitor": 0,
           "regions": [{"id": "main", "x_pct": 0, "y_pct": 0,
                        "w_pct": 70, "h_pct": 100}, ...]}

        Use list_layout_presets() to see the available preset names.

        Slot naming: preset layouts yield human-readable named slot ids
        derived from the preset definition (e.g. "left", "center", "right").
        Positional layout types use generated positional names:
          columns → col-0, col-1, col-2, …
          rows    → row-0, row-1, …
          grid    → r0c0, r0c1, r1c0, r1c1, … (compact rRcC format)
        regions use the "id" value supplied in each region dict.
        """
        if isinstance(spec, str):
            raise ValueError(
                'spec must be a layout dict or a list of dicts, not a plain string. '
                'For a preset use {"type": "preset", "name": "<name>"}; '
                "call list_layout_presets() for valid names."
            )
        try:
            return MANAGER.compute_layout(spec)
        except (ValidationError, TypeError) as exc:
            raise ValueError(
                'Invalid layout spec. spec must be a layout dict or a list of dicts. '
                'For a preset use {"type": "preset", "name": "<name>"}; '
                f"call list_layout_presets() for valid names. Original error: {exc}"
            ) from exc

    @mcp.tool()
    def apply_layout(
        spec: LayoutSpec,
        target_desktop: Optional[Union[int, str]] = None,
    ) -> list[dict]:
        """Compute the layout and set it as the active layout for the given
        desktop (default: current). Unlike ``compute_layout`` (preview-only),
        this call persists the layout so that slot ids become targetable by
        ``move_window`` and ``launch_*``. Returns the list of slot rectangles.

        Spec grammar (see compute_layout for full details):
          {"type": "preset",  "name": "three-columns", "monitor": 0}
          {"type": "columns", "splits": [25, 50, 25],  "monitor": 0}
          {"type": "grid",    "cols": 2, "rows": 2,    "monitor": 0}
          ...or a list of such dicts for multi-monitor layouts.

        Slot naming: preset layouts yield human-readable named slot ids
        derived from the preset definition (e.g. "left", "center", "right").
        Positional layout types use generated positional names:
          columns → col-0, col-1, col-2, …
          rows    → row-0, row-1, …
          grid    → r0c0, r0c1, r1c0, r1c1, … (compact rRcC format)
        regions use the "id" value supplied in each region dict.

        This does NOT move any existing windows — call move_window or launch_*
        to fill the slots.
        """
        return MANAGER.apply_layout(spec, target_desktop)
