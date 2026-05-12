# Security Policy

## Threat model

`vdesktop-plugin` is a **local** MCP server. It runs as a Windows process
launched by an MCP client (typically Claude Code) on the same machine as the
user, with the user's own privileges. It does not listen on a network socket
and is not designed to be exposed beyond the host.

The trust boundary is the MCP client: anything that can reach the server's
stdio already runs as the user. Such a client can read the user's files,
spawn arbitrary processes, and otherwise act with the user's authority — with
or without this plugin. The plugin's tools are accordingly authority-equivalent
to "the user runs commands themselves."

## Intentional shell execution

`launch_terminal` exposes a `tab.command` field that is forwarded verbatim to
the shell the tab opens with:

| `shell` | What runs `tab.command`           |
| ------- | --------------------------------- |
| `wsl`   | `bash -lc <command>` inside WSL   |
| `powershell` | `powershell.exe -NoExit -Command <command>` |
| `cmd`   | `cmd.exe /K <command>`            |
| _none_  | the profile's default shell       |

This is the **point** of a terminal launcher: open a terminal and run something
in it. Shell metacharacters in `command` are *expected* to be interpreted by
the shell. This is not an injection bug; it is the documented contract. Do not
file a vulnerability for "I can run arbitrary code through `tab.command`."

## Defended fields

These fields are **not** shell-executed and are constrained to a safe
identifier charset (`^[A-Za-z0-9 _.\-]{1,128}$`):

- `tab.profile` — Windows Terminal profile name
- `tab.wsl_distro` — WSL distribution name
- `launch_terminal(window_title=...)` — title tag used to resolve the new window

Bypassing those — getting a stray quote or semicolon to escape the argv
boundary in `wt.exe` / `wsl.exe` parsing — *would* be a bug worth reporting.

## Out of scope

- Process spawning via `launch_app` and the dedicated launchers (Chrome,
  VS Code, Windows Terminal) is by design.
- Path conversion in `pathmap.py` does not sanitize against unusual filesystem
  names; the underlying Windows APIs handle those.

## Reporting a vulnerability

For anything that breaks the defended fields above, or any other unexpected
authority escalation, open a GitHub issue with the label `security` (or a
private security advisory if the repository supports them).
