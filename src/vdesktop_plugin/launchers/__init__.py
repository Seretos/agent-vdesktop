"""App launchers — each registers an MCP tool that spawns a process,
resolves its HWND, optionally moves it to a target desktop and slot, then
registers it in the tracking registry."""
from __future__ import annotations


def register(mcp) -> None:
    from . import chrome, edge, generic, terminal, vscode

    chrome.register(mcp)
    edge.register(mcp)
    terminal.register(mcp)
    vscode.register(mcp)
    generic.register(mcp)
