# pstack model configuration

These are the canonical pstack role defaults. The Cursor slugs below express model, effort, and speed preferences; resolve them through the live harness catalog and supported controls as described in `PORT.md`. They are not required providers or exact-version pins. Recognized role lines from `~/.config/pstack/models.md` override individual defaults. `inherit-parent` and `auto` use the parent chat model with no model override. Honor older configurations during invocation and suggest setup once when their defaults marker is missing or older.

Arena runners and interrogate reviewers create one arm per comma-separated entry, including aliases, subject to the workflow's disclosed unavailable-seat fallback. Commas inside a role name belong to that name. The arena cross-judge pool supplies at most one judge from another vendor, in pool order. Fable and other Claude models share a vendor, although Fable is a separate family for runner fallback. `inherit-parent` and `auto` never judge. On rejection, try the nearest valid route of the same family, then the next eligible pool entry, or skip and disclose the judge. With an unknown parent, try the first real route and disclose that the vendor check did not run. Preserve explicit user choices, repeated models, and aliases; disclose limited diversity.

```text
# defaults: 3
# budget: large (xhigh)
feature, refactoring: claude-opus-5-5-xhigh-fast
bug-fix: claude-opus-5-5-xhigh-fast
perf-issue: claude-opus-5-5-xhigh-fast
hillclimb: claude-opus-5-5-xhigh-fast
judgment and prose: claude-opus-5-5-xhigh-fast
arena runners: claude-fable-5-2-high, claude-opus-5-5-high-fast, gemini-4-carbon-high
arena cross-judge pool: claude-opus-5-5-high-fast, gemini-4-carbon-high
swarm workers: claude-opus-5-5-high-fast
interrogate reviewers: claude-fable-5-2-high, claude-opus-5-5-high-fast, gemini-4-carbon-high
```

`large` keeps each role's default effort, `medium` lowers it one step, and `small` lowers it two on `xhigh` > `high` > `medium` > `low`, clamped at `low`. No role runs above `xhigh`; panel seats keep their listed level at invocation. Resolve Opus 5.5's fast preference and Gemini's `high` ceiling through supported controls, not invented IDs. Verification uses `swarm workers`. Outside a panel, Fable 5.2 runs only when the user names it for the task or after two Opus 5.5 xhigh runs of the same brief fail their check; disclose which condition applies. Aliases retain the parent model. At setup, write only detected routes or aliases; at invocation, preserve the workflow's disclosed fallbacks.
