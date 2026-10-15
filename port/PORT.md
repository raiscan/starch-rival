# pstack portability adapter

Read this once when loading a pstack skill. It adapts poteto's Cursor workflows to Codex and Claude Code. It takes precedence over conflicting platform names, model defaults, and fallback rules in the preserved upstream text. User instructions, repository instructions, available tools, and host permissions take precedence over workflow defaults. Follow an already authorized delivery flow without adding generic approval ceremonies.

## Scope and invocation

The upstream skills, playbooks, references, agents, and assets remain together. Only packaging, setup, model routing, and missing Cursor integrations are adapted. Consult the bundled upstream guide for the workflows themselves.

Preserve each skill's original invocation policy. A skill marked `disable-model-invocation: true` stays explicit-only in Claude Code; Codex receives the equivalent `policy.allow_implicit_invocation: false` in its `agents/openai.yaml`. Such a skill can still be read when an explicitly loaded workflow names it as a step. For example, poteto-mode calls unslop for its replies. Unslop does not become a rule for every conversation, and how does not become universally implicit. Invoke skills through the current harness's skill mechanism rather than assuming Cursor slash commands exist.

## Models and the Sonnet reviewer

Read the bundled `models.md`, then overlay any recognized role lines in `~/.config/pstack/models.md`. Missing user lines retain the bundled defaults, not the Cursor model table. Keep the upstream role names. `inherit-parent` and `auto` mean the current parent model; omit a model override. Panel entries each create one arm, including alias entries. The default panels have two arms.

Concrete model names identify a provider model, not a promise that a Cursor slug or reasoning suffix works in another harness. Discover actual routes before use. Set reasoning effort and speed only through supported controls; never fabricate model slugs. User configuration can choose other available models for ordinary roles.

**Claude Sonnet 5.5 is the required independent reviewer.** The `interrogate reviewers` panel includes `claude-sonnet-5-5`. In poteto-mode, obtain one read-only independent Sonnet 5.5 review of the final substantive code or workflow changes before completing delivery. An interrogate review of that same final state satisfies this requirement; do not commission a duplicate review. Supply the user's intent, full relevant diff, surrounding contracts, and completed checks. The lead evaluates findings and owns any changes. Re-review only when a material finding or subsequent change leaves relevant risk unresolved.

This requirement does not apply to unrelated conversations or routine prose edits. Do not add a preflight approval step. If Sonnet 5.5 is unavailable, continue independent implementation and checks, then report the exact review blocker. Never silently substitute Opus, another Sonnet version, or the parent model, and never claim the required review completed. Changing this pin requires an explicit user decision.

## Delegation

When T3 orchestration is exposed, use `orchestrator_capabilities` to discover current provider instances and model IDs, including configured custom models. Use native subagents for a same-provider model when supported. For Claude reviews from Codex, or another unsupported native route, use T3 `delegate_task` with the discovered provider instance and exact `claude-sonnet-5-5` model. Read-only is a task constraint even when a tool lacks a read-only flag; reviewers must not edit files, commit, install, or invoke delivery actions.

Keep the returned `taskId`, use `task_status` or `task_cancel` as needed, and prefer completion notifications to polling. Each new review round is a new `delegate_task` call with the original brief, prior findings, responses, and unresolved objections. Give each round a distinct `clientRequestId`, stable across retries of that round. A returned `childThreadId` is backing storage; do not send it a continuation or create an ordinary top-level conversation to act as a reviewer.

If T3 is unavailable, native Claude Code may provide the exact model through `--model claude-sonnet-5-5`. Use the available temporary-agents skill for its registry, saved session identity, expiry, bounded execution, and cleanup. Do not copy credentials, weaken permission modes, or leave idle processes running. If neither route supports that exact model, report the blocker.

For a code/helper delegate that upstream calls a `poteto-agent`, use that registered role when available. Otherwise give the delegate the full bundled `agents/poteto-agent.md` persona and the absolute path to the installed `skills/poteto-mode/SKILL.md`; it must read that skill before work. The supplied path replaces the persona's Cursor plugin discovery. Routed skills keep their own reviewer/explorer roles rather than becoming poteto-agent delegates. Map upstream `Task` fields to supported controls and bounded tasks, not literal tool calls that the harness lacks.

## Cursor integrations

- `~/.cursor/rules/pstack-models.mdc` means `~/.config/pstack/models.md` here. This file is loaded by pstack, not installed as a global always-applied harness rule. Setup changes only that model file after the user chooses the proposed changes.
- `create-skill` means the available `skill-creator` capability. If absent, follow the harness's documented skill format and validate the resulting skill; do not require another plugin merely for the Cursor name.
- `deslop` means a bounded cleanup of the task's changed code using available tools or an existing relevant skill. Remove unnecessary complexity and accidental scaffolding, preserve behavior, and run checks affected by any edits. Installing `cursor-team-kit` is not a prerequisite.
- `control UI`, `control CLI`, Cursor terminals, and runtime proof mean the harness's available project/runtime controls. Use an existing test harness or owned isolated runtime when appropriate. Respect repository desktop, browser, and input restrictions; a workflow does not authorize controlling an unrelated shared desktop.
- Todo, question, background-task, and file-editing instructions use supported equivalents. A missing UI affordance does not require a new dependency or permission ceremony.
- PR monitoring uses an available native watcher and its notifications instead of building a competing polling loop. In T3, register created or actively worked-on PRs with `link_pull_request` when exposed; honor the current tool instructions for `watch_pull_request` and handoff. Do not infer authorization to merge, publish, message others, or create schedules from an upstream playbook example.
- `skills/poteto-mode/scripts/worktree-audit.sh` reads Cursor transcripts and uses macOS `stat`/`date` options. It is preserved source, not a portable authority for worktree cleanup. Use `git worktree`, Git status, and harness-owned session evidence instead. Missing Cursor history never proves a Codex or Claude worktree disposable. Preserve unknown, ignored, uncommitted, and unmerged work according to user/repository policy.

## Installation and updates

The build creates separate `dist/codex/` and `dist/claude/` packages. Codex metadata preserves unsupported upstream frontmatter under `metadata` and encodes invocation policy in `agents/openai.yaml`; Claude retains its native frontmatter. Both packages include this adapter, bundled model defaults, and the whole upstream supporting tree. Their skill names match directory names.

Fetching upstream prepares source for review. It never changes installed skills. Keep adaptation in `port/` and tooling; update `upstream/` only from the pinned canonical source. Reconcile changed workflows with these boundaries, run the port checks, and obtain the required Sonnet review before offering an update for integration. Scheduling and installation are separate actions with the user's chosen scope.
