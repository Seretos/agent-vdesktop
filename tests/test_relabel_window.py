"""Regression tests for the relabel_window null-string coercion bug (#22).

The bug: FastMCP's pre-parser calls json.loads() on string arguments whose
type annotation is not exactly `str`. When the annotation was `Optional[str]`,
passing the literal string "null" caused json.loads("null") -> None, so the
label was cleared instead of stored verbatim.

Fix: change the annotation to plain `str` so the pre-parser short-circuits
(guard: `field_info.annotation is not str`), then map empty string -> None in
the body to provide the clear-label path.

These tests drive the real FastMCP argument-validation pipeline via
`func_metadata` + `call_fn_with_arg_validation`, so they would FAIL on the
pre-fix `Optional[str]` signature.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.utilities.func_metadata import func_metadata


def _get_relabel_window_fn():
    """Return the real relabel_window function from the registered tools.

    We register against a minimal stand-in and capture the decorated function,
    which is the one FastMCP's pipeline will validate args for.
    """
    captured: dict = {}

    class CaptureMCP:
        def tool(self, name=None):
            def deco(fn):
                # Only capture relabel_window
                if fn.__name__ == "relabel_window":
                    captured["fn"] = fn
                return fn
            return deco

    with patch("vdesktop_plugin.tools.windows.MANAGER"):
        from vdesktop_plugin.tools import windows as window_ops
        window_ops.register(CaptureMCP())

    return captured["fn"]


def _call_via_fastmcp(fn, arguments: dict):
    """Run fn through FastMCP's full argument-validation pipeline synchronously."""
    meta = func_metadata(fn)
    return asyncio.run(
        meta.call_fn_with_arg_validation(
            fn,
            fn_is_async=False,
            arguments_to_validate=arguments,
            arguments_to_pass_directly=None,
        )
    )


# ---------------------------------------------------------------------------
# Regression test: the reported bug
# ---------------------------------------------------------------------------

def test_null_string_stored_verbatim():
    """Regression: the literal string 'null' must be forwarded to the engine
    as the string 'null', not coerced to Python None via json.loads."""
    mock_manager = MagicMock()
    mock_manager.relabel_window.return_value = {}

    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        fn = _get_relabel_window_fn()
        _call_via_fastmcp(fn, {"handle_id": "h1", "new_label": "null"})

    mock_manager.relabel_window.assert_called_once_with("h1", "null")


# ---------------------------------------------------------------------------
# Clear-label path: empty string -> engine receives None
# ---------------------------------------------------------------------------

def test_empty_string_clears_label():
    """An empty string sentinel must map to None so the engine clears the label."""
    mock_manager = MagicMock()
    mock_manager.relabel_window.return_value = {}

    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        fn = _get_relabel_window_fn()
        _call_via_fastmcp(fn, {"handle_id": "h1", "new_label": ""})

    mock_manager.relabel_window.assert_called_once_with("h1", None)


# ---------------------------------------------------------------------------
# Normal path: arbitrary non-empty string stored verbatim
# ---------------------------------------------------------------------------

def test_normal_label_stored_verbatim():
    """Any non-empty, non-null string is forwarded to the engine unchanged."""
    mock_manager = MagicMock()
    mock_manager.relabel_window.return_value = {}

    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        fn = _get_relabel_window_fn()
        _call_via_fastmcp(fn, {"handle_id": "h1", "new_label": "some-label"})

    mock_manager.relabel_window.assert_called_once_with("h1", "some-label")
