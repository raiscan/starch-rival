# Automation

The repository's source, portability adapters, baking tools, tests, and upstream maintenance instructions live in [baking/](baking/README.md). The ready-to-use translated packages live at the repository root in [codex/](../codex/) and [claude/](../claude/).

An existing Hermes cron handles upstream checks and candidate preparation. See the [baking guide](baking/README.md) for its replacement precheck command and task path, and the [maintenance lifecycle](baking/sync-task.md) for its candidate-only scope. The live schedule, model selection, reporting destination, and run history remain managed in Hermes.
