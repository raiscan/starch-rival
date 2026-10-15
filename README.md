# Starch Rival

Ready-to-use Codex and Claude Code translations of [pstack](https://github.com/cursor/plugins/tree/main/pstack), created by **Lauren Tan ([poteto](https://github.com/poteto))**.

The complete translated packages are tracked here: [Codex](codex/) and [Claude Code](claude/), each with 54 skills and the upstream supporting materials. Start with [Codex poteto-mode](codex/skills/poteto-mode/SKILL.md) or [Claude poteto-mode](claude/skills/poteto-mode/SKILL.md). The translations preserve the current upstream workflows and use a small adapter for platform metadata, model routing, setup, and Cursor-specific integrations. Starch Rival is independently maintained and is not an official pstack distribution.

## Install and use

Use Linux or macOS with Python 3.9+, Git, and [PyYAML](automation/baking/requirements.txt):

```bash
git clone --recurse-submodules https://github.com/raiscan/starch-rival.git
cd starch-rival
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r automation/baking/requirements.txt
```

For an existing clone, initialize the pinned source before validation or installation:

```bash
git submodule update --init -- automation/baking/upstream
```

Install from the clean primary checkout on `main`. Omit either target if you only use one tool:

```bash
python3 automation/baking/scripts/pstack.py install --target codex --target claude
```

Installation validates and copies the tracked packages; it does not rebake them. It creates an immutable snapshot under `.cache/installed/` and links skill directories into `~/.codex/skills/` or `~/.claude/skills/`. Concrete local Markdown references become absolute paths within that snapshot, so supporting materials remain available through the skill links. Keep this checkout at its installed path. A conflicting existing skill is reported rather than overwritten. The installer requires a clean primary `main` checkout and leaves user model files, trust, and scheduler settings unchanged.

In a new session, use `$poteto-mode` in Codex or `/poteto-mode` in Claude Code. Invoke `setup-pstack` to choose model or reasoning-budget overrides. Upstream's explicit-only skills stay explicit-only. Bundled [model defaults](codex/models.md) apply immediately; optional overrides belong in `~/.config/pstack/models.md`.

Ordinary delegates inherit the parent model. Two-arm review includes exact `claude-sonnet-5-5`; substantive code and workflow edits under poteto-mode require its independent review. T3 discovers and delegates the cross-provider model. Native Claude Code is a fallback when T3 is unavailable, with the temporary-agents lifecycle. An unavailable Sonnet 5.5 route is reported as a review blocker. Model review is an agent workflow requirement; packaging tools do not certify that it occurred. Read the bundled [adapter](codex/PORT.md) for the full portability rules.

## Maintain the translations

The source, adapters, baking tools, tests, and Hermes maintenance instructions live in [automation/baking/](automation/baking/README.md). `bake` explicitly refreshes the tracked `codex/` and `claude/` packages; `build` remains an alias. Validation checks those packages against the pinned source and defined adaptations. Edit the source adapters and tooling, then rebake rather than hand-editing the packages.

The canonical source is the Git submodule at [automation/baking/upstream/](automation/baking/upstream/), with the package at `automation/baking/upstream/pstack/`. Its [manifest](automation/baking/upstream.json) records commit [`e5136d8`](https://github.com/cursor/plugins/tree/e5136d82418d2db3165ea1050d17577cd618cc05) and the matching pstack subtree hash. The source stays verbatim. The [pinned upstream guide](https://github.com/cursor/plugins/blob/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/docs/guide/README.md) explains the workflows, and [AGENTS.md](AGENTS.md) defines repository delivery boundaries.

An existing Hermes cron checks upstream and prepares reviewed candidates. Its live configuration and run history belong to Hermes. The [baking guide](automation/baking/README.md) provides the replacement repository paths for that job; changing this checkout does not update the live cron. Integration and installation remain separate actions under the owner's chosen scope.

## License and attribution

[MIT](LICENSE). The pstack workflows, playbooks, agent prompts, and supporting materials are Lauren Tan's work; their [original license](https://github.com/cursor/plugins/blob/e5136d82418d2db3165ea1050d17577cd618cc05/pstack/LICENSE) is preserved in the pinned submodule and baked packages. Starch Rival adds the portability adapter, packaging, installation, and sync tooling. This port is published at [raiscan/starch-rival](https://github.com/raiscan/starch-rival).
