# Starch Rival portability adapter

Read this once when loading a pstack skill. It adapts poteto's Cursor workflows to Codex and Claude Code. Use these translations where the preserved upstream text assumes Cursor-specific tools, model slugs, or setup. User instructions, repository instructions, available tools, and host permissions take precedence over workflow defaults. Follow an already authorized delivery flow without adding generic approval ceremonies.

## Canonical harness documentation

The preserved upstream README and `docs/harness/claude-code.md` describe canonical pstack, not Starch Rival. Where they conflict with this adapter, use this adapter: install `starch-rival@starch-rival`, use `/starch-rival:<name>` in Claude Code, keep model overrides in `~/.config/pstack/models.md`, and discover supported models and tools rather than assuming a fixed Claude-only catalog. Native Claude registers no agents; use the persona fallback below instead of assuming `pstack:poteto-agent` or `pstack:comment-sicko` exists. Do not run canonical harness generators or write global Claude rules for this port. Preserved Cursor-only automation materials remain references, not portable services; skip unavailable integrations with a brief explanation without claiming their work ran.

## Scope and invocation

The upstream skills, playbooks, references, agents, and assets remain together. Only packaging, setup, model routing, and missing Cursor integrations are adapted. Consult the bundled upstream guide for the workflows themselves. Starch Rival's project-maintenance policies do not become requirements for projects using this plugin.

Preserve each skill's original invocation policy. A skill marked `disable-model-invocation: true` stays explicit-only in Claude Code; Codex receives the equivalent `policy.allow_implicit_invocation: false` in its `agents/openai.yaml`. Such a skill can still be read when an explicitly loaded workflow names it as a step. For example, poteto-mode calls unslop for its replies. Unslop does not become a rule for every conversation, and how does not become universally implicit. Invoke skills through the current harness's skill mechanism rather than assuming Cursor slash commands exist. Native plugin skills belong to Starch Rival: select `poteto-mode` from that plugin in the Codex skill picker, or use `/starch-rival:poteto-mode` in Claude Code. The native Claude manifest sets `agents: []`; preserved Cursor agent prompts remain supporting references rather than automatically registered agents.

## Models

Read the bundled `models.md`, then overlay any recognized role lines in `~/.config/pstack/models.md`. Missing user lines retain the canonical role defaults. Keep the upstream role names. `inherit-parent` and `auto` mean the current parent model; omit a model override. Arena runners, architect runners, and interrogate reviewers create one arm per configured entry, including aliases. The arena cross-judge pool supplies one judge, preferring a different model family from the parent's when possible.

The canonical model table expresses defaults, not required providers or exact model versions. Discover actual routes before use: a Cursor slug or reasoning suffix may not work in another harness. Map model, reasoning effort, and speed to supported provider controls; never fabricate model slugs. User configuration can choose other available models for every role.

Preserve each workflow's model fallback behavior. For example, Interrogate falls back from a rejected configured model to its family's default, then to the closest supported equivalent when a default is unavailable, preferring the same family and reasoning tier. Disclose substitutions and keep the review moving rather than blocking on a model slug. A table-maintenance PR mentioned upstream is subject to the user's delivery instructions. Preserve configured aliases and panel counts; disclose limited model diversity rather than silently rewriting user choices. If no delegation route exists, report that limitation without claiming a review ran. This adapter adds no review stage or pinned reviewer.

## Delegation

Use the current harness's model discovery and delegation tools. When T3 orchestration is exposed, `orchestrator_capabilities` includes provider instances and configured custom models that a native subagent list may omit. Use native subagents when they support the selected model, or app-owned delegation for an unsupported native or cross-provider route. Follow the live tools' task lifecycle and permission instructions. Read-only is a task constraint even when a tool lacks a read-only flag; reviewers must not edit files, commit, install, or invoke delivery actions.

For a code/helper delegate that upstream calls a `poteto-agent`, use that registered role when available. Otherwise give the delegate the full bundled `agents/poteto-agent.md` persona and the absolute path to the installed `skills/poteto-mode/SKILL.md`; it must read that skill before work. The supplied path replaces the persona's Cursor plugin discovery. Routed skills keep their own reviewer/explorer roles rather than becoming poteto-agent delegates. Map upstream `Task` fields to supported controls and bounded tasks, not literal tool calls that the harness lacks.

## Cursor integrations

- `~/.cursor/rules/pstack-models.mdc` means `~/.config/pstack/models.md` here. This file is loaded by pstack, not installed as a global always-applied harness rule. Setup changes only that model file after the user chooses the proposed changes.
- `create-skill` means the available `skill-creator` capability. If absent, follow the harness's documented skill format and validate the resulting skill; do not require another plugin merely for the Cursor name.
- `deslop` means a bounded cleanup of the task's changed code using available tools or an existing relevant skill. Remove unnecessary complexity and accidental scaffolding, preserve behavior, and run checks affected by any edits. Installing `cursor-team-kit` is not a prerequisite.
- `control UI`, `control CLI`, Cursor terminals, and runtime proof mean the harness's available project/runtime controls. Use an existing test harness or owned isolated runtime when appropriate. Respect repository desktop, browser, and input restrictions; a workflow does not authorize controlling an unrelated shared desktop.
- Todo, question, background-task, and file-editing instructions use supported equivalents. A missing UI affordance does not require a new dependency or permission ceremony.
- PR monitoring uses an available native watcher and its notifications instead of building a competing polling loop. In T3, register created or actively worked-on PRs with `link_pull_request` when exposed; honor the current tool instructions for `watch_pull_request` and handoff. Do not infer authorization to merge, publish, message others, or create schedules from an upstream playbook example.
- `skills/poteto-mode/scripts/worktree-audit.sh` reads Cursor transcripts and uses macOS `stat`/`date` options. It is preserved source, not a portable authority for worktree cleanup. Use `git worktree`, Git status, and harness-owned session evidence instead. Missing Cursor history never proves a Codex or Claude worktree disposable. Preserve unknown, ignored, uncommitted, and unmerged work according to user/repository policy.
