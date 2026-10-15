# pstack for Codex and Claude Code

A local port of [poteto's canonical pstack](https://github.com/cursor/plugins/tree/main/pstack), with a small compatibility layer and a **Claude Sonnet 5.5 reviewer**. The upstream workflows stay intact; this does not import the community fork's added policies.

The source snapshot and its commit/tree identity live in [`upstream/`](upstream/) and [`upstream.json`](upstream.json). Our changes live in [`port/`](port/). Read the [adapter](port/PORT.md) for exact differences and the [upstream guide](upstream/docs/guide/README.md) for the workflows.

## Build and install

Python 3, Git, and [PyYAML](requirements.txt) are required. Install `requirements.txt` in your preferred Python environment, then check and build the development tree:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/pstack.py build
```

After integration, install from the clean primary checkout on `main`:

```bash
python3 scripts/pstack.py install --target codex --target claude
```

The build creates `dist/codex/` and `dist/claude/`, each containing the entire upstream package and its adapter. The installer refuses a dirty checkout, a linked worktree, or a branch other than `main`. It takes an immutable snapshot under `.cache/installed/` and links its skill directories into `~/.codex/skills/` or `~/.claude/skills/`. Concrete local Markdown links point to absolute paths in that snapshot so supporting references survive skill symlinks. A subsequent build cannot change active skills. Keep this checkout at its installed path. The installer does not register the Cursor plugin or modify global instructions, trust, models, or scheduler settings. A conflicting existing skill is reported rather than overwritten.

In a new session, invoke `setup-pstack` to choose model changes, then invoke `poteto-mode` for work in poteto's style. Use the current harness's skill invocation syntax. Upstream's explicit-only skills stay explicit-only. Bundled [model defaults](port/models.md) apply immediately; optional overrides belong in `~/.config/pstack/models.md`.

Ordinary delegates inherit the parent model. Two-arm review includes exact `claude-sonnet-5-5`; substantive code and workflow edits under poteto-mode require its independent review. T3 discovers and delegates the cross-provider model. Native Claude Code is a fallback when T3 is unavailable, with the temporary-agents lifecycle. An unavailable Sonnet 5.5 route is reported as a review blocker, never silently substituted. Model review is an agent workflow requirement; the Python tooling validates packaging rather than certifying that review occurred.

## Keep up with poteto

```bash
python3 scripts/pstack.py check
python3 scripts/pstack.py prepare-sync
```

Both maintenance commands resolve the primary checkout through Git's worktree inventory and share its lock, cache, and candidate directory, even when launched from a scheduler-created worktree. Pin the scheduled job to that primary maintenance checkout. `check` compares the canonical pstack subtree, so unrelated monorepo changes are a no-op. `prepare-sync` creates or reuses a `feature/ai-upstream-<tree12>` branch in `.worktrees/upstream-<tree12>` and updates only the upstream snapshot and manifest. It leaves the candidate uncommitted for an agent to reconcile and review. Fetching does not update installed skills.

When the changed upstream tree already has a valid prepared candidate, `check` returns `candidate_pending`, `changed: true`, `wakeAgent: false`, and its path. The scheduled job reports or suppresses that pending result instead of commissioning the same adaptation, tests, and review again. This does not prove review succeeded or restart a failed agent; explicitly resume that candidate when needed. A newer upstream tree gets a separate candidate, preserving the older one.

The [sync task](automation/sync-task.md) gives an agent the bounded update procedure. The [automation options](automation/README.md) explain existing Claude, Codex, and Hermes scheduling rather than adding a daemon. No scheduler is activated by this repository. It currently has no publishing remote configured; cloud scheduling or PR delivery needs a separately chosen repository and destination.

## Maintain the port

Edit `port/`, `scripts/`, or `tests/`; regenerate `dist/` rather than editing it. Preserve upstream files verbatim and refresh them through the sync tooling. Before integration, run the Python safety suite, build both variants, check generated references and invocation metadata, and obtain the required Sonnet 5.5 review. Build validation compares the complete supporting-file inventory, bytes, and executable modes, accounting for the defined adaptations. See [AGENTS.md](AGENTS.md) for repository boundaries.
