# Bake and maintain Starch Rival

This directory owns the canonical source pin, portability adapters, independent port version, baking and delivery tools, safety tests, and the existing Hermes job's lifecycle. The complete translated packages are tracked at the repository root in [codex/](../../codex/) and [claude/](../../claude/).

## Source and layout

- `upstream/` is the canonical `cursor/plugins` Git submodule; its package is `upstream/pstack/`. Keep source files verbatim. GitHub's gitlink opens the [pinned canonical repository](https://github.com/cursor/plugins/tree/d457567332aa6989e753ea289f30ea2bfbc80bc0).
- [upstream.json](upstream.json) records that commit and pstack subtree hash. `prepare-sync` advances it with the gitlink in an isolated candidate.
- [release.json](release.json) owns the Starch Rival semantic version, initially `0.1.0`, independently of canonical pstack's version.
- [port/](port/) contains only consumer-facing platform, setup, and model-routing adaptations. [PORT.md](port/PORT.md) preserves canonical workflow policy; this repository's reviewer and publication requirements belong in [sync-task.md](sync-task.md#independent-review).
- [scripts/pstack.py](scripts/pstack.py) bakes, validates, installs legacy snapshots, retires owned legacy links, and prepares source candidates. [scripts/delivery.py](scripts/delivery.py) refreshes primary `main` and publishes agent-reviewed candidates. [tests/](tests/) covers these contracts.

Maintenance uses Python 3.9+, Git, and [PyYAML](requirements.txt). All command paths below are relative to the repository root:

```bash
python3 -m pip install -r automation/baking/requirements.txt
git submodule update --init -- automation/baking/upstream
```

Initialize the source in each task worktree and repeat after integration moves its pin. Preserve local work without `--force`. Baking and validation require the initialized source to match the manifest and gitlink; they do not fetch implicitly. Native plugin users consume the tracked packages and do not need a source checkout or Python environment.

### Migration from the former layout

An older clone may still have root `upstream/`. Before pulling the layout change, inspect `git -C upstream status --porcelain --untracked-files=all --ignored`, preserve local work, and deinitialize that clean source with `git submodule deinit -- upstream`. Pull the integrated branch, then initialize `automation/baking/upstream`. If the change was already pulled, preserve any leftover untracked root `upstream/` outside the checkout before initializing the new path. Unknown contents are never disposable; a leftover directory prevents clean-checkout delivery.

## Baking and publication checks

A release advances the port version before baking and review:

```bash
python3 automation/baking/scripts/pstack.py bump-version
python3 automation/baking/scripts/pstack.py bake
python3 -m unittest discover -s automation/baking/tests -v
python3 automation/baking/scripts/pstack.py validate
```

`bump-version` defaults to the next patch; `--version MAJOR.MINOR.PATCH` selects a strictly newer version. `build` remains an alias for `bake`. Baking refreshes `codex/`, `claude/`, and both root native marketplace catalogs. Both plugins identify as `starch-rival@starch-rival`, carry the port version, and preserve canonical attribution and provenance. The Claude manifest registers skills and sets `agents: []`, keeping the verbatim Cursor agent prompts as supporting references.

Validation compares the instructions, native manifests, provenance, complete supporting inventory, bytes, and executable modes against the source and adaptations. After explicitly staging all intended source, adapter, tooling, documentation, catalog, and baked changes, the publication check is:

```bash
python3 automation/baking/scripts/pstack.py validate --tracked
```

That check also matches every expected baked file, marketplace catalog, and release metadata file to Git's index bytes and modes. Preserved upstream `.gitignore` files can hide new supporting files; stage only those required paths explicitly with `git add -f -- <specific-file>`. A locally valid bundle must survive publication and a clean clone.

Exact Sonnet 5.5 independently reviews the final staged contents and completed checks before publication. One review of unchanged final work is enough; an unavailable exact model is a blocker. The reviewed tree comes from `git write-tree`. Tooling compares publication with that tree but cannot attest that the review occurred. [sync-task.md](sync-task.md) gives the existing job's full lifecycle and precise publication command.

## Existing Hermes job

The existing Hermes cron keeps its recorded primary maintenance checkout, selected Sol model, schedule, reviewer access route, credentials, reporting destination, and history. Its repository precheck is:

```bash
python3 automation/baking/scripts/delivery.py precheck
```

The precheck fast-forwards clean primary `main` from `origin/main`, refreshes an already-installed native Codex plugin through its configured Git marketplace when available on the same host, then performs the canonical pstack subtree check. Its final JSON retains `wakeAgent`, including `false` for unchanged or pending candidates. Errors remain visible. Hermes runs on another host; [workstation delivery](../updates/README.md) refreshes native installations here.

For a changed tree, `pstack.py prepare-sync` prepares a source candidate; Sol reconciles and versions it, then baking, staging, tests, validation, and exact independent review precede `delivery.py publish`. The owner's authorization covers reviewed commits, fast-forward integration into primary `main`, integrated verification, and pushing only `main`. It does not cover PRs, plugin installation from candidates, or changes to user models, credentials, trust, or schedules. Pending work is preserved for explicit resumption, not retried on every tick. Failures and cleanup still required are reported as remaining work.

## Legacy snapshot installer

The earlier installer remains an explicit fallback:

```bash
python3 automation/baking/scripts/pstack.py install --target codex --target claude
```

It requires clean primary `main`, validates the baked packages without rebaking, and copies them into immutable `.cache/installed/` snapshots. Owned skill links point there, with concrete local Markdown references rewritten to absolute paths. Native plugin updaters do not update these links. After verifying native installation, `pstack.py retire-links --target codex --target claude` removes only this checkout's legacy links; immutable snapshots, user directories, and foreign links remain intact. Baking and candidate preparation cannot mutate active legacy skills.
