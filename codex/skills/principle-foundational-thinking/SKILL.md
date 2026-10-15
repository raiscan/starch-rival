---
name: principle-foundational-thinking
description: 'Apply before writing logic: choosing core types and data structures,
  sequencing scaffold-vs-feature work, asking what concurrent actors share. Get the
  data structures right so downstream code becomes obvious.'
---

## Local harness adapter

Read [PORT.md](../../PORT.md) before applying Cursor-specific tool, model, or setup instructions. It also defines this port's Sonnet 5.5 reviewer. User, repository, and live tool instructions take precedence.

# Foundational Thinking

**Structural decisions** protect option value. **Code-level decisions** protect simplicity.

**Data structures first.** Get the data shape right before writing logic. Define core types early, trace every access pattern, and choose structures that match the dominant paths.

At code level, DRY the structure, not every line. Types and data models should converge. Three similar statements still beat a premature abstraction. Prefer explicit over clever. Test behavior and edge cases, not line counts.

**Concurrency corollary.** Before sharing state between actors, ask "what happens if another actor modifies this concurrently?" If not "nothing", isolate.

**Scaffold first.** If something helps every later phase, do it first. Ask "does every subsequent phase benefit from this existing?" CI, linting, test infrastructure, and shared types are scaffold. Sequence for option value: setup before features, tests before fixes. Keep commits small and single-purpose.

Each increment should land a coherent abstraction or deepen one that exists. Do not spread a new capability across callers as special-case coordination.

Subtraction comes before scaffolding. Remove dead code first, then lay foundations.
