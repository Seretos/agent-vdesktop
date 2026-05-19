# agent-vdesktop

MCP server that lets AI coding agents control Microsoft Virtual Desktops on Windows 11. Ships as a self-contained Windows `.exe` (PyInstaller-frozen Python + pyvda + pywin32 + comtypes + uiautomation) so end users don't need a Python toolchain.

## Layout

```
src/vdesktop_plugin/            # Python source (src-layout)
  server.py                       # FastMCP entry point, wires the tools
  desktops.py                     # pyvda wrappers + pin-across-desktops
  windows.py                      # Win32 placement (SetWindowPos + DWM shadow correction)
  layouts.py                      # preset catalog + layout spec parser
  monitors.py                     # monitor enumeration & bounds
  adoption.py                     # registering pre-existing windows
  query.py                        # find windows by title / Chrome tab content
  tracking.py                     # in-memory handle_id ↔ label registry
  pathmap.py                      # POSIX ↔ Windows path conversion (for WSL)
  launchers/                      # per-app: chrome, edge, terminal, vscode, generic
  _win32_helpers.py, _window_classes.py

tests/                          # pytest, runs on every push (test.yml)
scripts/build.ps1               # PyInstaller wrapper + smoke test + optional packaging
vdesktop.spec                   # PyInstaller config
pyproject.toml                  # setuptools (package-dir = src/) + pytest config
.claude-plugin/plugin.json      # plugin manifest (name, version, description)
.mcp.json                       # MCP server config, auto-discovered at plugin root

.github/workflows/
  test.yml                      # pytest on every push and PR
  release.yml                   # manual-dispatch full release flow
  dispatch.yml                  # manual recovery: re-send marketplace dispatch
```

## Branches

- `main` — source of truth. All edits go here.
- `release` — orphan branch, force-pushed by `release.yml`. Contains only install-ready files: `.claude-plugin/plugin.json`, `bin/vdesktop.exe`, `README.md`. Clients clone at the version tag (e.g. `v0.0.1`), which lives on a release-branch commit.

The release branch shares no history with main. Don't try to merge between them.

## Release flow

Triggered manually:

```
Actions → release → Run workflow → version=X.Y.Z
```

or `gh workflow run release.yml -f version=X.Y.Z`.

The workflow:
1. Validates `X.Y.Z` is semver.
2. Fails if tag `vX.Y.Z` already exists (delete it first if you really want to redo).
3. Stamps the version into `pyproject.toml` and `.claude-plugin/plugin.json` (CI checkout only — never pushed back to main).
4. Runs `scripts/build.ps1 -Clean -Package` (PyInstaller → smoke test → ZIP).
5. Stashes the ZIP outside the working tree (needed because step 6 wipes it).
6. Force-pushes the orphan `release` branch from the staged install-ready tree.
7. Creates the `vX.Y.Z` tag on that commit and a GitHub Release with the ZIP attached.
8. POSTs to `Seretos/agent-marketplace/dispatches` with the plugin metadata. (Direct POST because tags created via `GITHUB_TOKEN` don't trigger downstream workflows — Actions blocks it to prevent loops.)

`pyproject.toml`'s `version` field is **not** load-bearing for releases. The workflow input drives everything. Local devs can leave pyproject at whatever value.

## Build conventions (`scripts/build.ps1`)

- Compatible with **Windows PowerShell 5.1** (the system default) AND PowerShell 7. The CI runners use 7; local users may only have 5.1, so call it as `.\scripts\build.ps1` from a PS session rather than `pwsh -File ...`.
- No global `$ErrorActionPreference = 'Stop'` — PyInstaller writes heavily to stderr, which PS 5.1 wraps as ErrorRecord and would trip a global Stop.
- Python discovery prefers `py.exe -3` locally and `python.exe` in `$env:CI` (so `actions/setup-python` is honored).
- Bash heredocs for multi-line JSON dispatch payloads; PS heredocs are CRLF-quirky.
- The smoke test runs an MCP `initialize` handshake against the freshly built `.exe`. The build fails if the handshake fails.

## PyInstaller / src-layout notes

- The Python package is `vdesktop_plugin` under `src/`. `pyproject.toml` declares `package-dir = { "" = "src" }` and `[tool.pytest.ini_options] pythonpath = ["src"]`, so imports like `from vdesktop_plugin.X import Y` work directly.
- `vdesktop.spec` references `src/vdesktop_plugin/__main__.py` as the entry and `pathex=[ROOT / "src"]`. Adjust both if the layout ever moves.
- `pyvda`, `comtypes`, `uiautomation` are pulled in via `collect_all(...)` because they generate COM stubs lazily.

## Why a frozen .exe

`pyvda` calls undocumented `IVirtualDesktopManagerInternal` COM interfaces. The vtable changes between Windows builds, so `pyvda` needs pinning per Windows version. PyInstaller bundles a known-good combination so users don't `pip install` anything.

WSL doesn't change this — `binfmt_misc` intercepts `.exe` invocation and runs it on the Windows host. Same binary, same code path.

## Conventions

- Tests live in `tests/` and use pytest. They mostly cover deterministic logic (layouts, pathmap, tracking) — Win32 / COM paths are tested manually on real hardware.
- Don't add a `LICENSE` file without an explicit license decision. `build.ps1` references it but tolerates absence.
- Windows 10 is unsupported. Don't add Windows 10 compatibility branches — `IVirtualDesktopManagerInternal` semantics differ.
- The `dispatch.yml` workflow is a manual recovery tool only. Don't add automatic triggers to it.

## What lives where (for cross-repo reasoning)

- The marketplace contract (payload format) is in `agent-marketplace/AGENTS.md`. The "Dispatch to agent-marketplace" step in `release.yml` here must match it.
- `MARKETPLACE_DISPATCH_TOKEN` is a fine-grained PAT with `contents: write` + `pull-requests: write` on `Seretos/agent-marketplace`, stored as a repo secret here.
