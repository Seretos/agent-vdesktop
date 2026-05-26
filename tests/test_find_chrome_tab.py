"""Tests for find_chrome_tab wrapper behaviour: mutation-warning docstring
and the per-result 'adopted' flag (#38).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: register query tools against a minimal stand-in and capture
# the find_chrome_tab function.
# ---------------------------------------------------------------------------

def _get_find_chrome_tab_fn():
    """Return the real find_chrome_tab function from the registered tools."""
    captured: dict = {}

    class CaptureMCP:
        def tool(self, name=None):
            def deco(fn):
                if fn.__name__ == "find_chrome_tab":
                    captured["fn"] = fn
                return fn
            return deco

    with patch("vdesktop_plugin.tools.query.MANAGER"):
        from vdesktop_plugin.tools import query
        query.register(CaptureMCP())

    return captured["fn"]


# ---------------------------------------------------------------------------
# Regression: docstring must lead with the mutation/adoption warning
# ---------------------------------------------------------------------------

def test_find_chrome_tab_docstring_warns_mutation_at_top():
    """Regression #38: the docstring's opening (~200 chars) must clearly
    mention adoption/mutation/registry so callers are warned before reading
    the rest of the description."""
    fn = _get_find_chrome_tab_fn()
    doc = fn.__doc__
    opening = doc[:200].lower()

    assert "adopt" in opening or "registry" in opening or "write" in opening, (
        "find_chrome_tab docstring must warn about adoption/registry side-effect "
        f"in its first 200 characters; got: {doc[:200]!r}"
    )


# ---------------------------------------------------------------------------
# adopted=True when the window was NOT in the pre-call tracked set
# ---------------------------------------------------------------------------

def test_find_chrome_tab_adopted_flag_new_window():
    """When list_windows returns [] before the call, every matched window
    was not yet tracked, so adopted must be True for each result."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = []
    mock_manager.find_chrome_tab.return_value = [
        {"hwnd": 1234, "handle_id": "h1", "tab_index": -1,
         "tab_title": "GitHub", "window_title": "GitHub - Chrome"},
    ]

    with patch("vdesktop_plugin.tools.query.MANAGER", mock_manager):
        from vdesktop_plugin.tools import query
        # Re-register against a fresh MCP so we pick up the patched MANAGER.
        captured: dict = {}

        class CaptureMCP:
            def tool(self, name=None):
                def deco(fn):
                    if fn.__name__ == "find_chrome_tab":
                        captured["fn"] = fn
                    return fn
                return deco

        query.register(CaptureMCP())
        result = captured["fn"]("GitHub")

    assert len(result) == 1
    assert result[0]["adopted"] is True


# ---------------------------------------------------------------------------
# adopted=False when the window WAS already tracked before the call
# ---------------------------------------------------------------------------

def test_find_chrome_tab_adopted_flag_already_tracked():
    """When list_windows returns the same hwnd before the call, adopted must
    be False because the window was already in the registry."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [{"hwnd": 1234}]
    mock_manager.find_chrome_tab.return_value = [
        {"hwnd": 1234, "handle_id": "h1", "tab_index": -1,
         "tab_title": "GitHub", "window_title": "GitHub - Chrome"},
    ]

    with patch("vdesktop_plugin.tools.query.MANAGER", mock_manager):
        from vdesktop_plugin.tools import query

        captured: dict = {}

        class CaptureMCP:
            def tool(self, name=None):
                def deco(fn):
                    if fn.__name__ == "find_chrome_tab":
                        captured["fn"] = fn
                    return fn
                return deco

        query.register(CaptureMCP())
        result = captured["fn"]("GitHub")

    assert len(result) == 1
    assert result[0]["adopted"] is False


# ---------------------------------------------------------------------------
# Empty result — no crash
# ---------------------------------------------------------------------------

def test_find_chrome_tab_adopted_flag_empty_result():
    """When find_chrome_tab returns [], the wrapper must return [] cleanly
    without raising any exception."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = []
    mock_manager.find_chrome_tab.return_value = []

    with patch("vdesktop_plugin.tools.query.MANAGER", mock_manager):
        from vdesktop_plugin.tools import query

        captured: dict = {}

        class CaptureMCP:
            def tool(self, name=None):
                def deco(fn):
                    if fn.__name__ == "find_chrome_tab":
                        captured["fn"] = fn
                    return fn
                return deco

        query.register(CaptureMCP())
        result = captured["fn"]("no-match-pattern")

    assert result == []


# ---------------------------------------------------------------------------
# Mixed results — per-result adopted values
# ---------------------------------------------------------------------------

def test_find_chrome_tab_adopted_flag_mixed():
    """When results include one already-tracked hwnd and one new hwnd, each
    result's adopted flag reflects its individual tracking status."""
    mock_manager = MagicMock()
    # hwnd 1111 was already tracked; hwnd 2222 was not
    mock_manager.list_windows.return_value = [{"hwnd": 1111}]
    mock_manager.find_chrome_tab.return_value = [
        {"hwnd": 1111, "handle_id": "h1", "tab_index": 0,
         "tab_title": "Already Open", "window_title": "Already Open - Chrome"},
        {"hwnd": 2222, "handle_id": "h2", "tab_index": 1,
         "tab_title": "New Tab", "window_title": "New Tab - Chrome"},
    ]

    with patch("vdesktop_plugin.tools.query.MANAGER", mock_manager):
        from vdesktop_plugin.tools import query

        captured: dict = {}

        class CaptureMCP:
            def tool(self, name=None):
                def deco(fn):
                    if fn.__name__ == "find_chrome_tab":
                        captured["fn"] = fn
                    return fn
                return deco

        query.register(CaptureMCP())
        result = captured["fn"]("Tab")

    assert len(result) == 2
    by_hwnd = {r["hwnd"]: r for r in result}
    assert by_hwnd[1111]["adopted"] is False, "already-tracked window must have adopted=False"
    assert by_hwnd[2222]["adopted"] is True, "new window must have adopted=True"
