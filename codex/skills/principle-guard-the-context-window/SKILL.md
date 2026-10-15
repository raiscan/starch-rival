---
name: principle-guard-the-context-window
description: 'Apply when context is filling up: large outputs, long files, repeated
  reads, fan-out planning. Route bulk to subagents; keep summaries in the main thread,
  not raw payloads.'
---

## Local harness adapter

Read [PORT.md](../../PORT.md) before applying Cursor-specific tool, model, or setup instructions. It also defines this port's Sonnet 5.5 reviewer. User, repository, and live tool instructions take precedence.

# Guard the Context Window

**Why:** Context overflow degrades reasoning quality, creates compression artifacts, and halts progress.

**Pattern:**
- **Size phases and cap scope.** Limit files per phase, set turn budgets, account for mechanism costs.
