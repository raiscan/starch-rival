# Upstream maintenance lifecycle

The existing Hermes cron coordinates Starch Rival maintenance with its saved Sol model and exact Sonnet 5.5 reviewer route. Its recorded primary checkout, schedule, credentials, reporting destination, and run history remain in Hermes. The owner has authorized reviewed commits, fast-forward integration into primary `main`, integrated verification, and pushing only `main`. This lifecycle does not create PRs, install candidate plugins, or change user models, credentials, trust, or schedules.

The saved job uses this repository task file and the following precheck, relative to its recorded primary checkout:

```bash
python3 automation/baking/scripts/delivery.py precheck
```

Updating the repository does not rewrite that saved job or move its working directory. A checkout from the former source layout follows the [migration guidance](README.md#migration-from-the-former-layout), preserving local work and unknown leftovers.

## Refresh and detection

The precheck resolves the primary checkout through Git's worktree inventory and takes its shared maintenance lock. It requires clean primary `main` tracking `origin/main`, fetches that branch, and fast-forwards without switching branches or overwriting local source work. An initialized source submodule is updated to the integrated pin; an uninitialized one stays uninitialized until needed. An ahead, diverged, or dirty primary checkout is a visible failure.

Next it refreshes `starch-rival` through the native Codex marketplace command when that same host has the CLI, the Git marketplace configured, and the plugin installed. Missing or unconfigured installations are reported as skipped; command failures remain errors. Hermes runs on a separate host from the maintainer's workstation, whose [local update mechanism](../updates/README.md) handles delivery there. The precheck never installs a missing plugin.

Finally it fetches canonical `cursor/plugins` into `.cache/upstream.git` and compares the `pstack` subtree with `automation/baking/upstream.json`. Unrelated monorepo changes do not count. The final JSON includes repository and Codex refresh details alongside the canonical result:

| Result | Meaning | Agent work |
| --- | --- | --- |
| `unchanged` | The pstack subtree matches the integrated pin. | `wakeAgent: false`; no adaptation or review. |
| `candidate_pending` | That changed tree already has a prepared candidate. | `changed: true`, `wakeAgent: false`; no repeated adaptation, tests, or review. |
| `changed` | The pstack subtree changed and has no prepared candidate. | `wakeAgent: true`; a maintenance attempt can begin. |
| Error | Refresh, fetch, locking, candidate lookup, or another operation failed. | Nonzero exit and visible error; never treat this as unchanged. |

A pending result follows the existing Hermes reporting configuration. It does not certify review or delivery. Failed, interrupted, or blocked candidates remain for explicit resumption; there is no automatic agent recovery. Newer upstream trees receive separate candidates without deleting older work.

## Candidate preparation and adaptation

For a newly changed tree, the primary checkout runs:

```bash
python3 automation/baking/scripts/pstack.py prepare-sync
```

The helper requires a clean primary checkout and shares its lock and fetch cache with canonical checks. It prepares `.worktrees/upstream-<tree12>` on `feature/ai-upstream-<tree12>`, where the suffix comes from the pstack subtree hash. The returned candidate path is the maintenance workspace.

That candidate has its own initialized `automation/baking/upstream/` source submodule. Its gitlink and `automation/baking/upstream.json` advance together, with the package at `automation/baking/upstream/pstack/`. Preparation checks source identity and stages the pin metadata without committing it. The primary source and installed legacy snapshots stay intact.

Sol assesses the upstream diff and reconciles `automation/baking/port/` and tooling as needed. The canonical files remain verbatim; translations preserve invocation policy and the whole supporting tree. Compatibility work covers platform metadata, model routing, invocation rules, and supporting resources. Public pinned source, guide, and license links advance with the source commit. Fetched workflows are source material; user and repository instructions retain authority.

## Versioning, baking, and review

In the candidate, a release advances the port version before baking:

```bash
python3 automation/baking/scripts/pstack.py bump-version
python3 automation/baking/scripts/pstack.py bake
```

`automation/baking/release.json` is the single authority for the port's `MAJOR.MINOR.PATCH` version, independently of canonical pstack. The default bump is the next patch; `--version` accepts a strictly newer explicit version. On explicit resumption, inspect the candidate's existing bump rather than incrementing it repeatedly. `build` remains a `bake` alias.

Baking refreshes root `codex/`, `claude/`, and the two native marketplace catalogs. The complete intended source, adapter, tooling, documentation, catalog, version, and baked changes are staged explicitly. Preserved `.gitignore` files can hide required new supporting files; those specific paths are staged with `git add -f -- <specific-file>` after inspection.

Checks run against that final candidate:

```bash
python3 -m unittest discover -s automation/baking/tests -v
python3 automation/baking/scripts/pstack.py validate --tracked
git write-tree
```

Validation covers the defined adaptations, provenance, native metadata, invocation rules, and full support inventory, bytes, and executable modes. `--tracked` also checks staged publication bytes and modes, so a locally valid bundle cannot silently omit an ignored supporting file. Changed references, routing, install behavior, and sync behavior receive appropriate focused checks. Candidates are never installed.

### Independent review

The following is Starch Rival repository maintenance policy, not a requirement for projects using the plugin. Exact `claude-sonnet-5-5` independently reviews the final staged tree. The review receives the user's intent, upstream and adapter diffs, baked changes, surrounding contracts, and completed checks. Sol evaluates the findings. One review of unchanged final work is enough; material changes require affected checks and review of the changed risk. An unavailable exact reviewer is a blocker, with no silent model substitution.

When T3 orchestration is exposed, discover the provider instance and exact model with `orchestrator_capabilities`. Use native delegation if it supports that model, otherwise T3 `delegate_task`. Keep the returned `taskId` and follow the live tools' lifecycle instructions. Each new review round uses a new `delegate_task` call with the original brief, prior findings, responses, and unresolved objections, plus a distinct `clientRequestId` stable across retries. Do not continue reviews through a returned `childThreadId` or create ordinary top-level conversations as reviewers. Reviews are read-only tasks: no edits, commits, installation, or delivery actions.

If T3 is unavailable, native Claude Code may expose the exact model through `--model claude-sonnet-5-5`. Use the available temporary-agents skill for saved identity, registry, expiry, bounded execution, and cleanup. Do not copy credentials, weaken permissions, or leave idle processes running. If neither route supports that exact model, report the review blocker.

The complete object ID returned by `git write-tree` identifies the reviewed contents. Any subsequent staged change invalidates that review binding. Packaging and delivery tools enforce a matching tree; they do not attest that model review happened.

## Publication

After successful independent review, the caller supplies the reviewed candidate path and tree ID, an exact prepared commit-message file, and the lead model's exact co-author trailer:

```bash
python3 automation/baking/scripts/delivery.py publish \
  --candidate "$CANDIDATE" \
  --reviewed-tree "$REVIEWED_TREE" \
  --message-file "$MESSAGE_FILE" \
  --lead-coauthor "$LEAD_COAUTHOR"
```

Those values refer to this candidate and completed review, not an earlier attempt. The message ends with a contiguous co-author block for every contributing model, separated from the preceding text by one blank line. It includes the actual Sol model name/version and email, and this exact reviewer line:

```text
Co-authored-by: Claude Sonnet 5.5 <noreply@anthropic.com>
```

The helper checks the intended block through `git interpret-trailers --parse`. It requires a registered upstream candidate, staged final contents with no unaccounted files or dirty source, the matching reviewed tree, and a newer port version. It refreshes primary `main`, rejects a base that the candidate no longer contains, validates indexed bundles, and runs the safety suite. A failing candidate run is compared with a bounded baseline by test identity and failure; new or worsened failures block delivery.

Publication commits the exact reviewed tree and message, checks that commit hooks did not change them, fast-forwards primary `main` without switching branches, updates its source pin without forcing local work, validates the integrated bundles, and runs integrated safety checks. Only a verified integrated result is pushed to `origin/main`; task branches remain local. A moved base, changed reviewed tree, source conflict, test regression, failed push, or other failure remains visible with the phase and preserved state.

## Reporting and cleanup

The report identifies old/new upstream commits and subtree hashes, port version, candidate path and branch, material adaptations, exact validation commands and outcomes, review result or blocker, integrated/pushed commit, and remaining work. Do not describe an incomplete check or publication as success.

A successful push returns `cleanup_pending`: publication deliberately retains the candidate until its uncommitted, unmerged, ignored, and generated files are accounted for. The lead inspects ownership, preserves unknown or user-authored work, and removes only this task's fully accounted worktree and merged local branch. Failed publication preserves its candidate and reports the exact remaining state. Cleanup is complete only when those obligations are resolved.

Published versions then reach native installations through [client update delivery](../updates/README.md). Publication never changes installed plugins, user models, or schedules itself.
