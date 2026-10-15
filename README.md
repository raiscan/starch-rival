# Starch Rival

Friendly rivalry. Rigorous agent workflows.

Starch Rival is an unofficial compatibility port of [pstack](https://github.com/cursor/plugins/tree/main/pstack), created by **Lauren Tan ([poteto](https://github.com/poteto))**. It brings her workflows to **Codex and Claude Code**, with a small compatibility layer and an independent **Claude Sonnet 5.5 reviewer**.

The current snapshot contains 54 skills. The original source stays verbatim; the adapter handles platform metadata, model routing, setup, and Cursor-specific integrations. Starch Rival is independently maintained and is not an official pstack distribution.

[`upstream/`](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05) is a Git submodule of the canonical [`cursor/plugins`](https://github.com/cursor/plugins) repository. GitHub shows its pinned commit in this repository's file list and links to that source. The pstack package lives at `upstream/pstack/`; [`upstream.json`](upstream.json) records the matching commit and pstack subtree hash. Our changes live in [`port/`](port/). Read the [adapter](port/PORT.md) for exact differences and the [pinned upstream guide](https://github.com/cursor/plugins/blob/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/docs/guide/README.md) for the workflows.

## Build and install

Use Linux or macOS with Python 3.9+, Git, and [PyYAML](requirements.txt). Clone the repository and create a Python environment:

```bash
git clone --recurse-submodules https://github.com/raiscan/starch-rival.git
cd starch-rival
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

For an existing clone, initialize the pinned source before building:

```bash
git submodule update --init -- upstream
```

Run that command again after pulling an update that changes the submodule pin, and in each new task worktree before building. Preserve any local submodule work before updating; do not use `--force`. Build and validation commands require the initialized, unchanged pin and never fetch source implicitly.

Check and build both variants:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/pstack.py build
python3 scripts/pstack.py validate
```

Install at user level from the clean primary checkout on `main`. Omit either target if you only use one tool:

```bash
python3 scripts/pstack.py install --target codex --target claude
```

The build creates `dist/codex/` and `dist/claude/`, each containing the entire upstream package and its adapter. The installer refuses a dirty checkout, a linked worktree, or a branch other than `main`. It takes an immutable snapshot under `.cache/installed/` and links its skill directories into `~/.codex/skills/` or `~/.claude/skills/`. Concrete local Markdown links point to absolute paths in that snapshot so supporting references survive skill symlinks. A subsequent build cannot change active skills. Keep this checkout at its installed path. The installer does not register the Cursor plugin or modify global instructions, trust, models, or scheduler settings. A conflicting existing skill is reported rather than overwritten.

In a new session, use `$poteto-mode` in Codex or `/poteto-mode` in Claude Code for work in poteto's style. Invoke `setup-pstack` if you want to change models or reasoning budgets. Upstream's explicit-only skills stay explicit-only. Bundled [model defaults](port/models.md) apply immediately; optional overrides belong in `~/.config/pstack/models.md`.

Ordinary delegates inherit the parent model. Two-arm review includes exact `claude-sonnet-5-5`; substantive code and workflow edits under poteto-mode require its independent review. T3 discovers and delegates the cross-provider model. Native Claude Code is a fallback when T3 is unavailable, with the temporary-agents lifecycle. An unavailable Sonnet 5.5 route is reported as a review blocker, never silently substituted. Model review is an agent workflow requirement; the Python tooling validates packaging rather than certifying that review occurred.

## Keep up with poteto

```bash
python3 scripts/pstack.py check
python3 scripts/pstack.py prepare-sync
```

Both maintenance commands resolve the primary checkout through Git's worktree inventory and share its lock, cache, and candidate directory, even when launched from a scheduler-created worktree. Pin the scheduled job to that primary maintenance checkout. `check` compares the canonical pstack subtree, so unrelated monorepo changes are a no-op. `prepare-sync` creates or reuses a `feature/ai-upstream-<tree12>` branch in `.worktrees/upstream-<tree12>`, initializes that candidate's submodule, and updates its pin and manifest together. It leaves the candidate uncommitted for an agent to reconcile and review. The primary checkout's submodule and installed skills stay at their existing pins.

When the changed upstream tree already has a valid prepared candidate, `check` returns `candidate_pending`, `changed: true`, `wakeAgent: false`, and its path. The scheduled job reports or suppresses that pending result instead of commissioning the same adaptation, tests, and review again. This does not prove review succeeded or restart a failed agent; explicitly resume that candidate when needed. A newer upstream tree gets a separate candidate, preserving the older one.

An existing Hermes cron handles upstream maintenance. The [automation overview](automation/README.md) explains its role, and the [maintenance lifecycle](automation/sync-task.md) describes change detection, candidate preparation, validation, review, and reporting. The job prepares candidates; integration and installation remain separate. Its live configuration and run history belong to Hermes. This repository is published at [raiscan/starch-rival](https://github.com/raiscan/starch-rival); the upstream pin continues to track canonical pstack. Building or installing does not activate a scheduler or grant an agent permission to publish updates.

## Maintain the port

Edit `port/`, `scripts/`, or `tests/`; regenerate `dist/` rather than editing it. Preserve upstream files verbatim and refresh them through the sync tooling. Before integration, run the Python safety suite, build both variants, check generated references and invocation metadata, and obtain the required Sonnet 5.5 review. Build validation compares the complete supporting-file inventory, bytes, and executable modes, accounting for the defined adaptations. See [AGENTS.md](AGENTS.md) for repository boundaries.

## License and attribution

[MIT](LICENSE). The pstack workflows, playbooks, agent prompts, and supporting materials are Lauren Tan's work; their [original license](https://github.com/cursor/plugins/blob/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/LICENSE) is preserved in the pinned submodule. Starch Rival adds the portability adapter, packaging, installation, and sync tooling. Read [PORT.md](port/PORT.md) for the adaptations and local reviewer requirement.
