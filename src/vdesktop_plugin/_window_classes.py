"""Windows window-class name constants.

Centralized here so launchers, query, and adoption agree on the canonical
strings used to filter top-level windows by class.
"""
from __future__ import annotations

# Chrome (and Electron-derived apps like VS Code) use this class for their
# top-level frame.
CHROME_WIDGET_CLASS = "Chrome_WidgetWin_1"

# Windows Terminal's hosting window class.
TERMINAL_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"

# Mozilla Firefox top-level browser window class. Note this class alone is
# NOT unique — every Firefox window shares it — so launchers must combine it
# with either a stable spawn PID or a pre-spawn HWND snapshot.
FIREFOX_WINDOW_CLASS = "MozillaWindowClass"
