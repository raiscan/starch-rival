# Installed plugin updates

Publishing a reviewed Starch Rival version and delivering it to an installed client are separate parts of the update flow. The two native marketplaces both expose `starch-rival@starch-rival`; the packages come from the tracked root `codex/` and `claude/` directories.

Claude Code uses its native marketplace auto-update setting. Auto-update is enabled for the Starch Rival marketplace on the maintainer's installation. Claude refreshes the installed files during its normal update checks; an existing session retains its loaded version until reloading plugins or starting another session. Other users control this setting for their own installations. [Claude documentation](https://code.claude.com/docs/en/discover-plugins#keep-plugins-updated)

Codex exposes the native `codex plugin marketplace upgrade starch-rival` command. On the maintainer's Linux workstation, the existing user-systemd scheduler runs that command hourly using the [service](starch-rival-update.service) and [timer](starch-rival-update.timer) definitions in this directory. The timer catches a missed calendar run when the user's manager becomes active. It performs no model inference and only refreshes this marketplace. Failures appear in the service's systemd status and journal. The service assumes Codex is installed at `~/.local/bin/codex`; other installations can use their actual CLI path. [Codex marketplace documentation](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)

The Hermes maintenance job runs on a different host. Its precheck can refresh native Codex plugins when they are installed on that host, but the workstation timer supplies delivery here. The timer does not adapt source, run reviewers, publish changes, or install a plugin that has not already been selected. There is no second upstream-maintenance agent.

The [baking lifecycle](../baking/sync-task.md) covers Sol's upstream adaptation, exact Sonnet 5.5 review, version bump, and publication. Only published versions reach these native update mechanisms. An offline host or an unresolved source/review failure delays freshness; the last installed version remains available.

The earlier snapshot installer remains available for explicit local use. Its links are not managed by either plugin updater. During the native migration, the installer tooling retires only links owned by this checkout after the native plugins have been verified; immutable snapshots and unrelated skills remain in place.
