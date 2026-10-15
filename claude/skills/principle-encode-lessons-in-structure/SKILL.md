---
name: principle-encode-lessons-in-structure
description: Apply when you catch yourself writing the same instruction a second time,
  or notice a recurring correction. Encode the rule as a lint, metadata flag, runtime
  check, or script instead of more text.
disable-model-invocation: true
---

## Local harness adapter

Read [PORT.md](../../PORT.md) before applying Cursor-specific tool, model, or setup instructions. It also defines this port's Sonnet 5.5 reviewer. User, repository, and live tool instructions take precedence.

# Encode Lessons in Structure

If the lesson needs judgment and cannot be encoded, make the instruction more prominent and add an example of the failure mode.

**Corollary:** If the fix is structural, only use the structural fix. The instruction is the symptom.
