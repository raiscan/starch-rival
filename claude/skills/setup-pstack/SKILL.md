---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget.
  Detects your available models and writes an always-applied rule that overrides the
  skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget",
  or changing pstack's model choices.
---

## Local harness adapter

Read [PORT.md](../../PORT.md) before applying Cursor-specific tool, model, or setup instructions. User, repository, and live tool instructions take precedence.

# Setup pstack

Configure pstack's role choices in `~/.config/pstack/models.md`. Read the bundled `PORT.md` and `models.md` first. This replaces Cursor's global always-applied rule setup.

1. Discover the current harness's model routes. In T3 use `orchestrator_capabilities`, including its provider instances and configured custom models; the native subagent model list may be incomplete. Otherwise use the available provider's supported model discovery. If none can be detected, ask for the available routes. `inherit-parent` and `auto` are always valid. No provider or exact model version is required.
2. Read any existing `~/.config/pstack/models.md`. Treat its `# budget:` line and recognized role lines as the current choices, overlaying them on the bundled defaults. Identify retired role lines separately; do not silently discard unrelated content. An absent file needs no write until the user chooses changes.
3. Offer the upstream budget choices `unlimited`, `large`, `medium`, and `small`, targeting `max`, `xhigh`, `high`, and `medium`; `large` is the canonical default. Retain accepted role families, lists, and aliases on re-runs. Translate effort and speed through supported provider controls, using the nearest supported effort at or below the target in the same family. Mark unresolved routes as needing a choice. Do not append Cursor effort or speed suffixes to an unverified model ID.
4. Show every effective role and its resolved model, effort, and speed, marking unresolved defaults. Arena runners, architect runners, and interrogate reviewers create one delegate per list entry, aliases included, subject to the workflow's disclosed unavailable-seat fallback. The arena cross-judge pool supplies at most one judge from another model family: order it by preference; `inherit-parent` and `auto` never judge. Follow upstream's default-pool fallback and skip/disclose the judge when no eligible route runs; disclose when an unknown parent prevents the family check. Let the user accept the table or change any role and budget, offering detected concrete routes plus `inherit-parent` and `auto`. Existing authorization for specific choices is enough; do not ask again solely because setup is a skill.
5. Validate the proposed table, then write the chosen configuration with the same upstream role labels and a `# budget:` line. Update only pstack's model configuration. Preserve unrelated existing prose unless the user chose a whole-file replacement. Do not write Cursor rules, global instructions, implicit activation rules, project trust settings, credentials, or schedules.
6. Report the written path, the selected changes, and any unresolved route. Explain that pstack reads the file when its workflows load; an already running workflow may need to reload it. Re-running setup should preserve accepted choices.

As in upstream setup, an unavailable concrete choice must be resolved before writing it. This does not disable the workflows' invocation-time model fallbacks. The build and installer do not create or overwrite this user model file.

If the user needs proof against the real application and no project harness exists, offer upstream's optional verification-skill workflow once. Then, if the project has no formal verification skill (a project skill that runs a model checker, a proof, or another verifier against the code), offer `/create-formal-verification-skill` once. Invoke either generator only on acceptance; on refusal, move on without pushing. Do not install another plugin or create a new verification regime as an automatic setup step.
