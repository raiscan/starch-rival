# Bake and maintain Starch Rival

This directory contains the canonical source pin, portability adapters, Python tooling, tests, and instructions used by the existing Hermes maintenance job. The complete translated packages are tracked at the repository root in [codex/](../../codex/) and [claude/](../../claude/). Preserve the current translations and upstream supporting materials when updating them.

## Source and layout

- [upstream/](upstream/) is the canonical `cursor/plugins` Git submodule; its package is `upstream/pstack/`. Keep source files verbatim.
- [upstream.json](upstream.json) records the matching canonical commit and pstack subtree hash. Advance it with the gitlink through `prepare-sync`.
- [port/](port/) contains platform metadata, setup, and model-routing adaptations. Read [PORT.md](port/PORT.md) for the boundaries and exact `claude-sonnet-5-5` reviewer requirement.
- [scripts/pstack.py](scripts/pstack.py) owns baking, validation, installation, and sync preparation. [tests/](tests/) covers those contracts; [requirements.txt](requirements.txt) contains its Python dependencies.

All commands below run from the repository root. Use Python 3.9+, Git, and PyYAML. Install dependencies into your chosen Python environment:

```bash
python3 -m pip install -r automation/baking/requirements.txt
git submodule update --init -- automation/baking/upstream
```

Initialize the submodule in every new task worktree and repeat after integration changes its pin. Preserve local submodule work before updating; do not use `--force`. Baking and validation require the initialized source to match the manifest and gitlink; they never fetch implicitly.

### One-time migration from the former layout

In an existing clone that still has the source at root `upstream/`, inspect `git -C upstream status --porcelain --untracked-files=all --ignored` and preserve any local work first. Before pulling the layout change, deinitialize that clean source with `git submodule deinit -- upstream`. Pull the integrated branch, then initialize `automation/baking/upstream` with the command above. Git keeps the source repository in its module storage while changing the checkout path.

If the layout change was already pulled and left an untracked root `upstream/`, inspect and preserve that directory outside the checkout before initializing the new path. Do not delete unknown contents. A leftover directory makes the primary checkout dirty and prevents candidate preparation or installation.

## Refresh and verify the tracked packages

After changing adapters or preparing a new source pin, explicitly refresh both translated packages:

```bash
python3 automation/baking/scripts/pstack.py bake
python3 -m unittest discover -s automation/baking/tests -v
python3 automation/baking/scripts/pstack.py validate
```

`build` remains an alias for `bake`. Review and commit the resulting `codex/` and `claude/` changes with the source/adaptation changes. Validation compares the complete supporting-file inventory, bytes, and executable modes against the source and defined adaptations, including metadata, model routing, explicit invocation, and local references. Preserve upstream invocation policy and the existing translated prose.

Before integration, compare the validated package file inventory and executable modes with Git's staged inventory. Bundled upstream `.gitignore` files are preserved, so an expected new supporting file may need an explicit `git add -f -- <specific-file>` to be included. A locally valid package must also be complete in a clean clone.

For code developed in a worktree, follow the owner's delivery instructions: establish the updated-base full-suite baseline, run the development suite and focused checks, integrate into the main workspace's current branch without switching it, verify the integrated result against the baseline, push that branch, and account for all work before cleanup. Obtain the required independent read-only Sonnet 5.5 review for substantive code or workflow changes. One review of unchanged final work is enough; report an unavailable exact model as a blocker. Packaging tools do not certify that a model review occurred.

Installation is a separate action from baking:

```bash
python3 automation/baking/scripts/pstack.py install --target codex --target claude
```

The installer requires the clean primary checkout on `main`, validates the tracked baked packages, and copies them into an immutable `.cache/installed/` release. It never rebakes. Skill links point into that release, with concrete local Markdown references rewritten to absolute paths inside it. Baking or preparing another candidate cannot change active skills. Installation does not modify user models, trust, or the Hermes schedule; conflicting existing skills are reported.

## Existing Hermes job: replacement paths

Keep the already-configured Hermes job pinned to the primary maintenance checkout, `/home/farrell/code/projects/pstack`. The owner can pass these repository references to Hermes to replace the paths from the former layout:

```text
Working directory: /home/farrell/code/projects/pstack
Precheck: python3 automation/baking/scripts/pstack.py check --compact
Task instructions: /home/farrell/code/projects/pstack/automation/baking/sync-task.md
```

The task uses these commands from the appropriate checkout:

```bash
python3 automation/baking/scripts/pstack.py prepare-sync
# In the candidate path returned by prepare-sync:
python3 automation/baking/scripts/pstack.py bake
python3 -m unittest discover -s automation/baking/tests -v
python3 automation/baking/scripts/pstack.py validate
```

These are replacement paths for the existing job. Its cron identity, schedule, selected Sol model, credentials, reporting destination, and run history remain in Hermes; no cron update or other setup is performed by this repository change. Read [sync-task.md](sync-task.md) for precheck handling, candidate preparation, review, and reporting.

Both maintenance commands resolve the primary checkout through Git's worktree inventory and share its lock, `.cache/upstream.git`, and candidate directory. They compare only the canonical pstack subtree. Preparation initializes and advances only the candidate's source pin, preserving the primary checkout's submodule and installed skills. `candidate_pending` suppresses repeated agent work for an already-prepared tree; it does not certify a successful review or recover an interrupted agent. Explicit resumption may reuse that candidate. Newer upstream trees receive separate candidates without deleting older work.

The current Hermes scope ends with an uncommitted candidate and a report. Commits, pushes, PRs, merges, installation, user model-file edits, and schedule changes require their own authorized scope. Repository integration follows the owner's delivery instructions; successful candidate review alone does not publish or install an update.
