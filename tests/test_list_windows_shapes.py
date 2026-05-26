"""Regression tests for list_windows heterogeneous-shape normalisation (#37).

Before fix: the wrapper returned the raw lib output, which mixed two
incompatible record shapes — tracked rows (with handle_id) had pid=0,
unmanaged rows had a real pid but lacked tracked-window fields. No
discriminator field was present, so callers could not tell rows apart.

After fix: every row has a boolean `tracked` key; tracked rows with pid==0
have pid normalised to None.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: register window tools and capture list_windows
# ---------------------------------------------------------------------------

def _get_list_windows_fn():
    """Return the live list_windows function from the registered tools.

    Patches MANAGER during registration so no real COM calls happen, then
    returns the captured function. The caller should invoke the function
    inside its own ``with patch(..., mock_manager)`` block so the mock
    is active during the actual call.
    """
    captured: dict = {}

    class CaptureMCP:
        def tool(self, name=None):
            def deco(fn):
                if fn.__name__ == "list_windows":
                    captured["fn"] = fn
                return fn
            return deco

    with patch("vdesktop_plugin.tools.windows.MANAGER"):
        from vdesktop_plugin.tools import windows as window_ops
        window_ops.register(CaptureMCP())

    return captured["fn"]


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

def test_list_windows_tracked_row_has_tracked_true():
    """Regression #37: a tracked row (contains handle_id) must have tracked=True."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [
        {"handle_id": "h1", "label": "my-app", "pid": 0, "hwnd": 111,
         "slot_id": "s1", "state": "normal", "is_pinned": False,
         "is_app_pinned": False, "desktop_guid": "guid-1"},
    ]
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert result[0]["tracked"] is True


def test_list_windows_unmanaged_row_has_tracked_false():
    """Regression #37: an unmanaged row (no handle_id, real pid) must have tracked=False."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [
        {"hwnd": 999, "pid": 1234, "title": "Notepad", "class_name": "Notepad",
         "app_type": "unknown", "desktop_guid": "guid-1",
         "bounds": {"x": 0, "y": 0, "w": 800, "h": 600}},
    ]
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert result[0]["tracked"] is False


def test_list_windows_tracked_pid_zero_becomes_null():
    """Regression #37: tracked rows with pid==0 must have pid normalised to None."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [
        {"handle_id": "h1", "pid": 0, "hwnd": 111, "desktop_guid": "guid-1"},
    ]
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert result[0]["pid"] is None


def test_list_windows_every_row_has_tracked_key():
    """Regression #37: in a mixed list every row must carry the tracked key."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [
        {"handle_id": "h1", "pid": 0, "hwnd": 111, "desktop_guid": "guid-1"},
        {"hwnd": 999, "pid": 5678, "title": "Notepad", "class_name": "Notepad",
         "app_type": "unknown", "desktop_guid": "guid-1",
         "bounds": {"x": 0, "y": 0, "w": 800, "h": 600}},
    ]
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert all("tracked" in row for row in result)


def test_list_windows_tracked_nonzero_pid_preserved():
    """Regression #37: tracked rows with a real (non-zero) pid must keep that value."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [
        {"handle_id": "h2", "pid": 1234, "hwnd": 222, "desktop_guid": "guid-1"},
    ]
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert result[0]["pid"] == 1234


def test_list_windows_unmanaged_pid_preserved():
    """Regression #37: unmanaged rows must have their pid unchanged."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = [
        {"hwnd": 777, "pid": 9999, "title": "Explorer", "class_name": "CabinetWClass",
         "app_type": "unknown", "desktop_guid": "guid-1",
         "bounds": {"x": 0, "y": 0, "w": 1920, "h": 1080}},
    ]
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert result[0]["pid"] == 9999


def test_list_windows_empty_result():
    """Regression #37: when lib returns [] the wrapper must return [] cleanly."""
    mock_manager = MagicMock()
    mock_manager.list_windows.return_value = []
    fn = _get_list_windows_fn()
    with patch("vdesktop_plugin.tools.windows.MANAGER", mock_manager):
        result = fn()
    assert result == []


def test_list_windows_docstring_has_discriminator_field():
    """Regression #37: 'tracked' must appear in the list_windows docstring."""
    fn = _get_list_windows_fn()
    assert "tracked" in fn.__doc__, (
        "list_windows docstring must document the 'tracked' discriminator key"
    )


def test_list_windows_docstring_pid_null_for_unknown():
    """Regression #37: docstring must state that pid is null/None for tracked
    windows when the PID is unknown."""
    fn = _get_list_windows_fn()
    doc = fn.__doc__.lower()
    assert "null" in doc or "none" in doc, (
        "list_windows docstring must mention that pid is null/None for unknown PIDs"
    )
