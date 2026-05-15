"""Tests for vdesktop_plugin.launchers.generic._resolve_working_directory.

The public ``launch_app`` MCP tool relies on this helper to validate the
caller-supplied ``working_directory`` before spawning a process. We test
the helper directly because the spawn pipeline pulls in ctypes.windll and
needs a real Windows host; the helper is pure path-handling code.

Like the other tests in this package these are Windows-only — generic.py
transitively imports ctypes.windll via _common.
"""
from __future__ import annotations

import os

import pytest

from vdesktop_plugin.launchers.generic import _resolve_working_directory


def test_returns_none_when_no_working_directory_given():
    assert _resolve_working_directory(None) is None


def test_returns_translated_windows_path_for_existing_dir(tmp_path):
    # tmp_path is an existing directory the test framework manages.
    result = _resolve_working_directory(str(tmp_path))
    assert result is not None
    assert os.path.isdir(result)


def test_raises_for_nonexistent_path(tmp_path):
    bogus = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="does not exist"):
        _resolve_working_directory(str(bogus))


def test_raises_for_path_that_is_a_file(tmp_path):
    f = tmp_path / "regular-file.txt"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        _resolve_working_directory(str(f))


def test_error_message_includes_caller_supplied_path(tmp_path):
    bogus = str(tmp_path / "missing")
    with pytest.raises(ValueError) as excinfo:
        _resolve_working_directory(bogus)
    # The user's spelling appears in the message so they can spot the typo.
    assert bogus in str(excinfo.value) or repr(bogus) in str(excinfo.value)
