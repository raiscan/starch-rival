# pstack model configuration

These are the canonical pstack role defaults. The Cursor slugs below express model, effort, and speed preferences; resolve them through the live harness catalog and supported controls as described in `PORT.md`. They are not required providers or exact-version pins. Recognized role lines from `~/.config/pstack/models.md` override individual defaults. `inherit-parent` and `auto` use the parent chat model with no model override.

Arena runners, architect runners, and interrogate reviewers create one arm per comma-separated entry, including aliases, subject to the workflow's disclosed unavailable-seat fallback. Commas inside a role name belong to that name. The arena cross-judge pool supplies at most one judge from another model family, in pool order, with the canonical default pool as fallback. `inherit-parent` and `auto` never judge. Skip the judge when no eligible route runs; disclose a skipped judge or an unknown-parent family check. Preserve explicit user choices, including repeated models or aliases, and disclose limited diversity.

```text
# budget: large (xhigh)
feature, refactoring: grok-4.7-xhigh-fast
bug-fix: grok-4.7-xhigh-fast
perf-issue: grok-4.7-xhigh-fast
hillclimb: grok-4.7-xhigh-fast
judgment and prose: claude-opus-5-5-xhigh
hardest tasks: claude-opus-5-5-xhigh
how explorer: grok-4.7-xhigh-fast
how explainer: claude-opus-5-5-xhigh
why investigators: grok-4.7-xhigh-fast
why synthesizer: claude-opus-5-5-xhigh
reflect tooling: grok-4.7-xhigh-fast
reflect judgment, divergent, synthesizer: claude-opus-5-5-xhigh
arena runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
arena cross-judge pool: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
swarm workers: grok-4.7-xhigh-fast
architect runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
interrogate reviewers: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
```

The budget labels `unlimited`, `large`, `medium`, and `small` target `max`, `xhigh`, `high`, and `medium` where supported. Apply the workflow's per-task effort and speed adjustments through supported controls. Aliases retain the parent model. At setup, write only detected concrete routes or aliases; at invocation, preserve the workflow's disclosed fallback behavior for unavailable models.
