# Starch Rival

Ready-to-use Codex and Claude Code translations of [pstack](https://github.com/cursor/plugins/tree/main/pstack), created by **Lauren Tan ([poteto](https://github.com/poteto))**.

The complete translated packages are tracked here: [Codex](codex/) and [Claude Code](claude/), each with 58 skills and the upstream supporting materials. Starch Rival preserves the workflows with a small adapter for platform metadata, model routing, setup, and Cursor integrations. It is independently maintained and is not an official pstack distribution.

## Install and use

Install the native `starch-rival@starch-rival` plugin from this repository's marketplace.

For Codex:

```bash
codex plugin marketplace add raiscan/starch-rival --ref main
codex plugin add starch-rival@starch-rival
```

For Claude Code:

```bash
claude plugin marketplace add raiscan/starch-rival
claude plugin install starch-rival@starch-rival --scope user
```

In a new session, select `poteto-mode` from Starch Rival in the Codex skill picker, or invoke `/starch-rival:poteto-mode` in Claude Code. Invoke `setup-pstack` to choose model or reasoning-budget overrides. Upstream's explicit-only skills stay explicit-only. Bundled [model defaults](codex/models.md) apply immediately; optional overrides belong in `~/.config/pstack/models.md`.

Claude Code can automatically update this custom marketplace when its auto-update setting is enabled in the marketplace controls or `extraKnownMarketplaces.starch-rival.autoUpdate` in user settings. Codex refreshes the installed version with `codex plugin marketplace upgrade starch-rival`. The maintainer's scheduled delivery is described in [installed plugin updates](automation/updates/README.md). Other users choose their own update cadence. Restart or reload the client session to use refreshed skills.

The port retains canonical pstack's role defaults as preferences, resolves them through the current harness's available models, and preserves each workflow's fallback behavior. Every role is configurable; the port adds no pinned reviewer or mandatory review stage. Read the bundled [adapter](codex/PORT.md) for the portability rules. The bundled Cursor agent prompts remain references; Claude's native plugin registers the skills and suppresses automatic registration of those agents. Starch Rival's own maintenance process below is separate from the workflows shipped to users.

### Legacy snapshot installation

The earlier installer remains an explicit fallback for Linux or macOS with Python 3.9+, Git, and [PyYAML](automation/baking/requirements.txt). In a recursive clone with dependencies installed, run from clean primary `main`:

```bash
python3 automation/baking/scripts/pstack.py install --target codex --target claude
```

It validates and copies the tracked packages into immutable `.cache/installed/` snapshots, with skill links under `~/.codex/skills/` or `~/.claude/skills/`. Concrete local Markdown references become absolute paths within that snapshot. Keep that checkout at its installed path. These links do not receive native plugin updates. After verifying the native plugins, `pstack.py retire-links --target codex --target claude` removes only legacy skill links owned by that checkout, preserving snapshots and foreign skills. Omit either target when migrating one client.

## Maintain the translations

The source, adapters, baking tools, tests, and Hermes lifecycle live in [automation/baking/](automation/baking/README.md). `release.json` owns the port's independent version, initially `0.1.0`; the canonical package has its own version. `bump-version` advances the port before `bake` refreshes both tracked packages and native marketplace metadata. Validation checks the complete packages and their staged publication contents. Edit adapters and tooling, then rebake rather than hand-editing the packages.

The canonical source is the Git submodule at `automation/baking/upstream/`, with the package at `automation/baking/upstream/pstack/`. Its [manifest](automation/baking/upstream.json) records commit [`c742dd6`](https://github.com/cursor/plugins/tree/c742dd61706fbacc1b95f1a20b7b988cf096ce6c) and the matching pstack subtree hash. The source stays verbatim. The [pinned upstream guide](https://github.com/cursor/plugins/blob/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack/docs/guide/README.md) explains the workflows, and [AGENTS.md](AGENTS.md) defines repository delivery boundaries.

An existing Hermes cron uses Sol to assess canonical changes, reconcile adaptations, bake and test a version, and obtain exact Sonnet 5.5 review. The owner has authorized that job to commit the reviewed candidate, fast-forward primary `main`, verify the integrated result, and push only `main`. The [maintenance lifecycle](automation/baking/sync-task.md) explains its checks and failure handling. Hermes runs on a separate host; its saved working directory, model, reviewer route, schedule, and run history remain authoritative. Repository changes take effect there after its next successful refresh; they do not rewrite the live job.

## License and attribution

[MIT](LICENSE). The pstack workflows, playbooks, agent prompts, and supporting materials are Lauren Tan's work; their [original license](https://github.com/cursor/plugins/blob/c742dd61706fbacc1b95f1a20b7b988cf096ce6c/pstack/LICENSE) is preserved in the pinned submodule and baked packages. Starch Rival adds the portability adapter, packaging, installation, and sync tooling. This port is published at [raiscan/starch-rival](https://github.com/raiscan/starch-rival).
