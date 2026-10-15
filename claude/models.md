# pstack model configuration

These bundled defaults override model tables in the upstream Cursor text. Recognized role lines from `~/.config/pstack/models.md` override individual bundled lines. `inherit-parent` and `auto` use the parent chat model with no model override. Each comma-separated panel entry creates one arm; commas inside the role name belong to that name.

Most roles inherit the current model. Arena and architect retain two perspectives, using the parent and Claude Opus 5.5; their concrete route must be available in the current catalog. Interrogate uses the parent and the user's pinned Claude Sonnet 5.5 reviewer. If the parent is already the other panel model, disclose the lack of model diversity and choose an available different family for the configurable arm. Keep Sonnet 5.5 in interrogate. See `PORT.md` for unavailable models and review requirements.

```text
# budget: inherit (use supported parent/default effort)
feature, refactoring: inherit-parent
bug-fix: inherit-parent
perf-issue: inherit-parent
hillclimb: inherit-parent
judgment and prose: inherit-parent
hardest tasks: inherit-parent
how explorer: inherit-parent
how explainer: inherit-parent
why investigators: inherit-parent
why synthesizer: inherit-parent
reflect tooling: inherit-parent
reflect judgment, divergent, synthesizer: inherit-parent
arena runners: inherit-parent, claude-opus-5-5
arena cross-judge pool: inherit-parent, claude-opus-5-5
swarm workers: inherit-parent
architect runners: inherit-parent, claude-opus-5-5
interrogate reviewers: inherit-parent, claude-sonnet-5-5
```

Concrete routes are validated through the live provider catalog at setup and invocation. Effort controls are separate from model IDs unless the provider explicitly exposes a combined slug. The budget labels `unlimited`, `large`, `medium`, and `small` preserve upstream's requested effort targets of `max`, `xhigh`, `high`, and `medium` where supported. They do not change aliases or manufacture unavailable routes. Sonnet's exact version stays pinned unless the user explicitly changes it.
