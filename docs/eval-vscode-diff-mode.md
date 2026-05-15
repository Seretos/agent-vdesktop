# Evaluation: VS Code diff mode for the worktree workflow

Issue: [#8](https://github.com/Seretos/agent-vdesktop/issues/8)
Scope: V2 evaluation only — no MCP code changes here. Output is this
document plus a Go / No-Go / Partial recommendation. A follow-up
implementation ticket is opened iff the recommendation is "go" or
"partial".

## Background

The orchestration use-case is: a Claude Code agent works inside a git
worktree branched from `main` (or another target branch) and produces a
commit or two. The user wants to **quickly visualise what the agent
changed** — including commits the agent already made — without spinning
up the full Editor workspace just to spelunk for changed files. The
question is whether VS Code's native diff mode is the right tool for that,
or whether a different visualiser is a better fit for AI-agent review.

## What we evaluated

Per the planning-phase decision **D1 Option A**, this evaluation
concentrates on **native VS Code CLI flags**. Extensions (GitLens, Git
Tree Compare, etc.) are mentioned for completeness but not exhaustively
benchmarked. We also widened the search per the user's follow-up
comment: if VS Code does not offer a good experience, what alternative
review tools are better suited to AI-agent-generated diffs?

The four investigation axes from the ticket:
1. CLI flags (`--diff`, `--goto`, `--wait`, `--dir-diff`).
2. VS Code extensions for the same workflow.
3. Behaviour when `working_directory` differs from the project root.
4. Behaviour when the opened location is a git worktree rather than the
   main repo.

## 1. Native VS Code CLI flags

| Flag | What it does | Fit for "show me what the agent changed" |
|---|---|---|
| `code --diff <a> <b>` | Opens a single side-by-side diff editor inside a new (or reused) window. | Works **per-file**. No native multi-file diff. |
| `code --dir-diff <dirA> <dirB>` | Opens a folder-level diff view. | Works for tree-vs-tree diffs but **does not understand git refs** — you have to materialise the two folders yourself. |
| `code --goto <file>:<line>` | Opens a file at a specific line. | Orthogonal — useful for navigation, not for review. |
| `code --wait` | Blocks until the window closes. | Useful as a git external `diff.tool`. |
| `code -n` | Forces a new window. | Already used by `launch_vscode` (`reuse_window=False`). |

Findings:

- **Per-file diffs work cleanly.** `code --diff <old-tmp-path> <new-path>`
  produces the familiar editor-style diff. The agent would have to
  `git show <ref>:<path>` each changed file to a temp location, then call
  `--diff` once per file. That is a lot of plumbing for a "quick look".
- **There is no native multi-file diff against a git ref.** `--dir-diff`
  is the closest thing, but it expects two filesystem directories. To
  diff the worktree against `origin/main` you'd have to `git worktree
  add` a second worktree at `origin/main` and point `--dir-diff` at it.
  That works, but you've now consumed two worktrees just to look at a
  diff.
- **`--wait` makes VS Code usable as `diff.tool`** (e.g.
  `git config diff.tool vscode; git difftool main..HEAD`). This *does*
  iterate through files one at a time inside the editor — the closest
  native solution to "show me everything that changed". But each file
  requires confirmation in the terminal and the experience is dominated
  by the editor chrome.

## 2. Extensions (surveyed, not benchmarked)

Per D1 these are only enumerated:

- **GitLens** — "Compare Branches" / "Compare with..." renders a tree
  of changed files with click-to-diff. Best in-editor experience, but
  the user has to first open the worktree as a full workspace and then
  navigate to the GitLens view. Heavy for "just show me the diff".
- **Git Tree Compare** (`letmaik.git-tree-compare`) — explicit tree
  view of working tree vs. branch/tag/commit. Closer to what we want
  conceptually; same caveat (full workspace needed).
- **Git Graph**, **Compare Folders** — similar trade-offs.

None of these can be invoked headlessly from the CLI without opening the
full workspace first. There is no `code --open-gitlens-compare main`
equivalent.

## 3. `working_directory != project root`

Tested via documentation review: `code <folder>` and `code --diff` both
take absolute paths; the spawning process's cwd has no influence on
which content is opened. Once issue #7 lands (`working_directory`
parameter on `launch_app`), it remains relevant only for downstream
processes like terminals or build scripts the spawned editor might
trigger — not for the editor's own file resolution.

## 4. Git worktrees

VS Code treats a git worktree like an ordinary folder: it picks up the
`.git` file (which points at the shared object store), source control
features work, and GitLens / Git Tree Compare are happy to compare
against `origin/main` from inside a worktree. No special-casing is
required from the MCP side — `launch_vscode(folder=<worktree-path>)`
already does the right thing. The only worktree-specific friction is
that some extensions display the worktree name as the workspace name,
which can be confusing if the worktree directory does not encode the
branch — that is a UX problem outside this evaluation's scope.

## Alternatives surveyed (per user follow-up)

The user asked: if VS Code diff mode is not satisfying, what tooling is
better suited to AI-agent review?

| Tool | Surface | Fit for AI-agent-diff review |
|---|---|---|
| [Difftastic](https://difftastic.wilfred.me.uk/) | Terminal, syntax-aware | **Best signal-to-noise.** Ignores formatting-only churn, so agent reformatting that pre-commit hooks fix up does not pollute the diff. Drop-in as `git config diff.external` or `GIT_EXTERNAL_DIFF`. Pure stdout output, no GUI. |
| [delta](https://github.com/dandavison/delta) | Terminal pager | Syntax-highlighted line diffs, side-by-side option, no AST awareness. Great for casual scanning of `git diff main..HEAD`. |
| [lazygit](https://github.com/jesseduffield/lazygit) / [gitui](https://github.com/extrawurst/gitui) | TUI | File-tree navigator + diff pane. Lazygit can pipe diffs through any external tool (delta, difftastic). Closest to "open a window, show me everything the agent did", with the trade-off that it is terminal-based. |
| [ftdv](https://crates.io/crates/ftdv/0.1.0) (2026) | TUI | Newer tool specifically targeting file-tree-based diff review, with pluggable backend (delta / difftastic / bat). Worth tracking; less mature than lazygit. |
| GitHub Desktop / GitKraken / Fork | GUI | Full git clients, heavyweight for "just look at the diff". |
| `code --diff` per-file | GUI | See §1. |

For an **AI-agent review loop** specifically, the winning combination
from the public discussion is **lazygit + difftastic** (or
**lazygit + delta** if syntax highlighting is enough): a single
keystroke opens the file tree, arrow keys walk the change set, the diff
pane shows semantically clean output, and committed-but-not-pushed
changes are first-class citizens. Cursor-style "approve hunks" panes
are explicitly *not* what the user is asking for (they optimise the
wrong loop — gating each hunk rather than scanning what the agent
did).

## Recommendation

**Partial-go for VS Code, plus a parallel option for an external diff
launcher.**

VS Code can do diff-mode, but only well for the **single-file** case
(`code --diff` + `--wait`). For the realistic worktree workflow —
"show me everything the agent changed since branching from `main`" —
the native CLI requires either:

- A custom orchestration that `git show`-s each changed file to a temp
  path and invokes `--diff` per file (high complexity, poor UX).
- Setting `git config diff.tool vscode` + `code --wait` and letting
  git iterate (works but is one-file-at-a-time and dominated by editor
  chrome).
- Opening the worktree as a full workspace and using GitLens /
  Git Tree Compare (heavy and contradicts the "without the full editor"
  intent of the original ticket).

External tools — specifically **lazygit (with delta or difftastic as
the diff backend)** — solve the use-case more directly and would fit
the vdesktop launcher pattern well (small TUI in a terminal slot,
quick to spawn, quick to close).

## Proposed follow-up tickets

Per D2 Option A, the follow-up ticket(s) include an API-sketch
proposal so the next plan cycle can iterate on the API surface rather
than re-deciding "should we do anything":

1. **`launch_vscode(..., mode="diff", diff_targets=[(left, right), ...])`** —
   single-file diff helper, runs `code --diff` per pair, optionally
   sequenced via `--wait` so the windows open in order. Low effort,
   solves the single-file case cleanly.
2. **`launch_lazygit(folder, *, diff_backend="delta"|"difftastic"|None, target_ref=None)`** —
   new dedicated launcher that spawns `wt.exe` with `lazygit` already
   pointed at the worktree, optionally pre-configured to diff against
   `origin/<target_ref>`. Reuses `launch_terminal`'s singleton-handling
   infrastructure. Highest impact for the agent-review use case.

The follow-up should be opened only after the user reviews this doc and
either accepts the recommendation or steers in a different direction.

## Sources

- VS Code: [Source Control overview](https://code.visualstudio.com/docs/sourcecontrol/overview),
  [Branches and Worktrees](https://code.visualstudio.com/docs/sourcecontrol/branches-worktrees)
- [Git Tree Compare extension](https://marketplace.visualstudio.com/items?itemName=letmaik.git-tree-compare)
- ["How to do a Diff in VS Code"](https://vscode.one/diff-vscode/)
- [Difftastic manual: Git integration](https://difftastic.wilfred.me.uk/git.html)
- [gitui — terminal Git UI](https://www.terminal.guide/tools/git-tool/gitui/)
- [ftdv on crates.io (2026)](https://crates.io/crates/ftdv/0.1.0)
