"""MCP tools for monitors and layout computation. Thin wrappers over
lib_python_vdesktop.VDesktopManager."""
from __future__ import annotations

from typing import Optional, Union

from lib_python_vdesktop import LayoutSpec

from ._engine import MANAGER


def register(mcp) -> None:
    @mcp.tool(name="list_monitors")
    def _list_monitors() -> list[dict]:
        """List all physical monitors with their bounds, work area, DPI, and primary flag.
        Indices are 0-based; the primary monitor is always index 0."""
        return MANAGER.list_monitors()

    @mcp.tool()
    def list_layout_presets() -> list[dict]:
        """List built-in layout preset names with a short description."""
        return MANAGER.list_layout_presets()

    @mcp.tool()
    def compute_layout(spec: LayoutSpec) -> list[dict]:
        """Resolve a LayoutSpec into concrete slot rectangles WITHOUT moving any
        windows. Useful for previewing a layout.

        A LayoutSpec is either ONE dict for one monitor, or a LIST of such
        dicts (one per monitor). Each dict must have a "type" key:

          {"type": "preset",  "name": "three-columns", "monitor": 0}
          {"type": "columns", "splits": [25, 50, 25],  "monitor": 0}
          {"type": "rows",    "splits": [50, 50],      "monitor": 0}
          {"type": "grid",    "cols": 2, "rows": 2,    "monitor": 0}
          {"type": "regions", "monitor": 0,
           "regions": [{"id": "main", "x_pct": 0, "y_pct": 0,
                        "w_pct": 70, "h_pct": 100}, ...]}

        Use list_layout_presets() to see the available preset names."""
        return MANAGER.compute_layout(spec)

    @mcp.tool()
    def apply_layout(
        spec: LayoutSpec,
        target_desktop: Optional[Union[int, str]] = None,
    ) -> list[dict]:
        """Compute the layout and remember it as the active layout for the given
        desktop (default: current). Returns the list of slot rectangles that
        subsequent launcher / move_window calls can target by slot_id.

        Spec grammar (see compute_layout for full details):
          {"type": "preset",  "name": "three-columns", "monitor": 0}
          {"type": "columns", "splits": [25, 50, 25],  "monitor": 0}
          {"type": "grid",    "cols": 2, "rows": 2,    "monitor": 0}
          ...or a list of such dicts for multi-monitor layouts.

        This does NOT move any existing windows — call move_window or launch_*
        to fill the slots.
        """
        return MANAGER.apply_layout(spec, target_desktop)
