# Upstream maintenance lifecycle

The existing Hermes cron coordinates a bounded maintenance attempt for Starch Rival. Hermes retains the job's schedule, selected Sol model, credentials, reporting destination, and run history. Keep its working directory pinned to the primary maintenance checkout, `/home/farrell/code/projects/pstack`, and use this task file at `/home/farrell/code/projects/pstack/automation/baking/sync-task.md`.

The replacement precheck is:

```bash
python3 automation/baking/scripts/pstack.py check --compact
```

These paths describe the repository side of the existing job. Changing this checkout does not update the live cron.

When migrating a checkout from the former root `upstream/` source, follow the [one-time migration guidance](README.md#one-time-migration-from-the-former-layout) before the next maintenance attempt. Preserve local source work and any leftover directory rather than deleting unknown contents.

## Detecting a change

From the primary checkout, the precheck resolves that checkout through Git's worktree inventory, takes its shared maintenance lock, and fetches canonical `cursor/plugins` into `.cache/upstream.git`. It compares the fetched `pstack` subtree hash with `automation/baking/upstream.json`. Changes elsewhere in the monorepo do not count as pstack updates.

The result controls whether an agent is needed:

| Result | Meaning | Agent work |
| --- | --- | --- |
| `unchanged` | The pstack subtree matches the integrated pin. | `wakeAgent: false`; no adaptation or review. |
| `candidate_pending` | That changed tree already has a prepared candidate. | `changed: true`, `wakeAgent: false`; no repeated adaptation, tests, or review. |
| `changed` | The pstack subtree changed and has no prepared candidate. | `wakeAgent: true`; a maintenance attempt can begin. |
| Error | A fetch, lock, candidate lookup, or other operation failed. | A nonzero exit and error remain visible; this is not an unchanged result. |

Report or suppress a pending result according to the existing Hermes reporting configuration. Do not start another maintenance agent or automatically recover failed or lost work for that tree. Explicit user resumption may reuse the candidate.

## Preparing the candidate

For a new changed tree, run from the primary checkout:

```bash
python3 automation/baking/scripts/pstack.py prepare-sync
```

The helper requires a clean primary checkout, shares its lock and fetch cache with `check`, and creates an isolated worktree at `.worktrees/upstream-<tree12>` on `feature/ai-upstream-<tree12>`. The suffix comes from the pstack subtree hash. Work only in the candidate path returned by the command.

The candidate has its own initialized `automation/baking/upstream/` submodule. Its gitlink and `automation/baking/upstream.json` advance together to the fetched canonical commit, with the package at `automation/baking/upstream/pstack/`. Preparation checks the source identity and stages the updated source metadata without committing it. The primary checkout's source and existing installed skill snapshots remain unchanged.

Sol assesses the upstream change and adapts `automation/baking/port/` and tooling where needed. Keep upstream files verbatim and preserve the current translations, upstream invocation policy, and complete supporting tree. Compatibility work covers platform metadata, model routing, invocation rules, and supporting resources. README's pinned canonical source, guide, and license links track the candidate commit. Fetched workflows remain source material; the owner's and repository's instructions retain authority.

## Baking, validation, and review

From the candidate's root, rebake its tracked packages before checks and review:

```bash
python3 automation/baking/scripts/pstack.py bake
python3 -m unittest discover -s automation/baking/tests -v
python3 automation/baking/scripts/pstack.py validate
```

`build` remains an alias for `bake`. Include the resulting root `codex/` and `claude/` changes in the candidate assessment. The safety suite and validation cover the affected packaging, sync, and installation behavior. Validation compares generated instructions and the full support-file inventory, bytes, and executable modes with the defined adaptations. Inspect generated references, model routing, explicit invocation, install collisions, and changed sync behavior as appropriate. Do not install the candidate.

For integration, compare the validated package inventory and executable modes with Git's staged files. Preserve the bundled `.gitignore` files and explicitly stage any expected ignored supporting file; validation of the working tree alone does not prove a clean clone will contain it.

Exact `claude-sonnet-5-5` supplies the independent read-only review described in [PORT.md](port/PORT.md). It receives the upstream and adapter changes, baked package changes, intent, and completed checks. Sol evaluates the findings; material changes or unresolved findings can justify another review. One review of unchanged final work is enough. An unavailable reviewer route leaves a reported blocker; never substitute another model or claim a successful review. The packaging tools do not attest that a model review occurred.

## Reporting and pending work

The maintenance report identifies the old and new upstream commits and subtree hashes, candidate path and branch, adaptations and baked changes, exact validation commands and outcomes, review outcome or blocker, and remaining actions. A successful attempt ends with an uncommitted candidate and a report. The current candidate-only scope excludes commits, pushes, PRs, merges, installation, user model-file edits, and schedule changes.

An existing candidate suppresses repeated work on later ticks for that tree. `candidate_pending` records its presence, not successful review or delivery. Failed, interrupted, or blocked work remains in place for explicit resumption; there is no automatic agent recovery or separate review-state ledger. A newer upstream tree receives a separate candidate without deleting older work.

Integration and installation occur separately under the user's delivery instructions. After integration changes the gitlink, initialize or update the primary submodule with `git submodule update --init -- automation/baking/upstream`, preserving local work without `--force`, before baking, validating, or installing. Installation from clean primary `main` validates and copies the baked packages into an immutable `.cache/installed/` release without rebaking. Preparing or rebaking candidates cannot modify active skills.
