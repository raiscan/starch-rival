# Automation

Starch Rival has two update stages. The existing Hermes cron maintains the port: Sol assesses canonical pstack changes, reconciles adaptations, bumps the port version, bakes and tests the packages, obtains exact Sonnet 5.5 review, and publishes the reviewed result to `main`. The [baking lifecycle](baking/sync-task.md) describes that bounded delivery flow and its failure handling; the [baking guide](baking/README.md) describes the source and tooling.

Native plugin updates deliver published versions to installed clients. Claude Code uses its marketplace auto-update setting. An hourly user-systemd timer refreshes the maintainer's configured Codex marketplace on the workstation without model inference. [Installed plugin updates](updates/README.md) explains those mechanisms and their limits.

Hermes runs on a different host. Its existing job retains its recorded working directory, selected Sol model, exact reviewer route, schedule, reporting destination, and run history. The repository's `delivery.py precheck` refreshes a clean primary checkout from `origin/main`, refreshes an already-configured native Codex plugin on that same host when available, then checks canonical pstack. Neither precheck nor publication installs plugins or changes user models, credentials, trust, or schedules.
