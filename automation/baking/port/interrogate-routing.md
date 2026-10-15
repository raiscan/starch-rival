## Step 3, Spawn Reviewers

Read the bundled `models.md`, then overlay recognized role lines from `~/.config/pstack/models.md`. The bundled role defaults apply when the user file or role line is absent. Do not use the preserved Cursor tables or model-family fallbacks for dispatch.

The `interrogate reviewers` line has two arms by default, the parent model and exact `claude-sonnet-5-5`. Keep the Sonnet 5.5 arm unless the user explicitly changes that requirement. A missing route leaves that review pending; do not substitute another model or call the panel complete.

Use the live provider catalog and delegation route in `PORT.md`. Give every reviewer the same scoped intent, diff, surrounding contracts, rubric, and read-only constraint. Use the supported reasoning and speed controls for that provider. An independent review is separate execution, even if its model matches the parent's.
