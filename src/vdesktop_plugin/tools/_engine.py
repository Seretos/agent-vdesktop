"""Shared engine handle for the MCP tool modules.

The plugin is a thin MCP wrapper: every tool delegates to this single
`VDesktopManager` instance from `lib_python_vdesktop`. The manager owns the
process-wide tracking registry, so all launch / adopt / move tools share state.

Behaviour, COM/Win32 calls, and the data model live in `lib_python_vdesktop` —
this package only re-supplies the MCP tool schemas (signatures + the
LLM-facing docstrings) and forwards to the manager.
"""
from __future__ import annotations

from lib_python_vdesktop import VDesktopManager

MANAGER = VDesktopManager()
