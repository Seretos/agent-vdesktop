"""App-launcher MCP tools — each registers a tool that delegates to
lib_python_vdesktop.VDesktopManager's launch_* methods."""
from __future__ import annotations


def register(mcp) -> None:
    from . import chrome, edge, generic, terminal, vscode

    chrome.register(mcp)
    edge.register(mcp)
    terminal.register(mcp)
    vscode.register(mcp)
    generic.register(mcp)
