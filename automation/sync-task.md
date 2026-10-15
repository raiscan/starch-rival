# Upstream maintenance lifecycle

The Hermes cron coordinates a bounded maintenance attempt for Starch Rival. The saved job definition in Hermes supplies its schedule, working directory, models, and reporting destination. This page describes how the precheck, candidate, validation, review, and report fit together.

## Detecting a change

The script precheck runs `python3 scripts/pstack.py check --compact`. The helper resolves the primary checkout through Git's worktree inventory, takes its maintenance lock, and fetches canonical `cursor/plugins` into `.cache/upstream.git`. It compares the fetched `pstack` subtree hash with `upstream.json`. Changes elsewhere in the monorepo do not count as pstack updates.

The result controls whether an agent is needed:

| Result | Meaning | Agent work |
| --- | --- | --- |
| `unchanged` | The pstack subtree matches the integrated pin. | `wakeAgent: false`; no adaptation or review. |
| `candidate_pending` | That changed tree already has a prepared candidate. | `changed: true`, `wakeAgent: false`; no repeated adaptation, tests, or review. |
| `changed` | The pstack subtree changed and has no prepared candidate. | `wakeAgent: true`; a maintenance attempt can begin. |
| Error | A fetch, lock, candidate lookup, or other operation failed. | A nonzero exit and error remain visible; this is not an unchanged result. |

## Preparing the candidate

For a new changed tree, `prepare-sync` creates an isolated worktree at `.worktrees/upstream-<tree12>` on `feature/ai-upstream-<tree12>`. The suffix comes from the pstack subtree hash. The helper requires a clean primary checkout and shares its lock and fetch cache with `check`.

The candidate has its own initialized `upstream/` submodule. Its gitlink and `upstream.json` advance together to the fetched canonical commit, with the package at `upstream/pstack/`. Preparation checks the source identity and stages the updated source metadata without committing it. The primary checkout's source and existing installed skill snapshots remain unchanged.

Sol then assesses the upstream change and adapts the portability layer where needed. Upstream files remain verbatim. The compatibility work covers platform metadata, model routing, invocation rules, and supporting resources. README's pinned canonical source, guide, and license links track the candidate commit. Fetched workflows remain source material; the owner's and repository's instructions retain authority.

## Validation and review

The candidate's Python safety suite, both harness builds, and package validation cover the affected packaging, sync, and installation behavior. Validation compares generated instructions and the full support-file inventory, bytes, and executable modes with the defined adaptations. Installation is not part of a scheduled candidate check.

Exact `claude-sonnet-5-5` supplies the independent read-only review described in [PORT.md](../port/PORT.md). It receives the upstream and adapter changes, intent, and completed checks. Sol evaluates the findings; material changes or unresolved findings can justify another review. An unavailable reviewer route leaves a reported blocker rather than a substituted model or a claimed successful review. The packaging tools do not attest that a model review occurred.

## Reporting and pending work

The maintenance report identifies the old and new upstream commits and subtree hashes, candidate path and branch, adaptations, validation results, review outcome or blocker, and remaining actions. A successful attempt ends with an uncommitted candidate and a report. The current candidate-only scope excludes commits, pushes, PRs, merges, installation, user model-file edits, and schedule changes.

An existing candidate suppresses repeated work on later ticks for that tree. `candidate_pending` records its presence, not successful review or delivery. Failed, interrupted, or blocked work remains in place for explicit resumption; there is no automatic agent recovery or separate review-state ledger. A newer upstream tree receives a separate candidate without deleting older work.

Integration and installation occur separately under the user's delivery instructions. After integration changes the gitlink, the primary submodule checkout must match that pin before building or installing. Installation from clean primary `main` creates an immutable release; preparing or rebuilding candidates cannot modify active skills.
