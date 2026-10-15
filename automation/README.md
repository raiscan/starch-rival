# Upstream maintenance

Starch Rival's upstream checks are scheduled by an existing Hermes cron. The maintenance flow uses Sol to reconcile changes from poteto's canonical pstack, with an independent review by exact `claude-sonnet-5-5`. It produces a candidate and a report for the repository owner.

The live schedule, selected Sol model, working directory, reporting destination, and run history are managed in Hermes. This directory explains the repository side of that workflow.

## From upstream to candidate

Each scheduled check compares the canonical `pstack` subtree with the pin in `upstream.json`. Unrelated changes elsewhere in `cursor/plugins` do not wake an agent. An unchanged tree skips agent work, and a tree with a pending candidate waits for action instead of triggering another adaptation and review. Fetch or tooling failures remain visible errors.

When a new pstack tree needs attention, Sol works in an isolated candidate. Its submodule pin and manifest advance together while the primary checkout's source and installed skills remain unchanged. Sol preserves upstream files verbatim, reconciles the compatibility layer, validates both harness packages, and obtains Sonnet 5.5 review. The report records the source change, candidate location, adaptations, checks, review outcome or blocker, and remaining work.

The [maintenance lifecycle](sync-task.md) explains the precheck results, candidate isolation, validation, review, and pending-work behavior in detail.

## Where automation stops

The current job's scope is candidate preparation and reporting. Commits, pushes, PRs, merges, installation, user model-file edits, and schedule changes remain outside that scope. A successful review does not itself publish or install an update.

Integration and installation are separate actions under the owner's delivery instructions. Installation from clean primary `main` creates an immutable release; existing skill links continue to use their current release until installation occurs. Building or installing the repository does not create or alter the Hermes cron.
