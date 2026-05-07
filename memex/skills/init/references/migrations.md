# Migration reference

> Referenced from the main init skill. Init detects an older `<!-- memex-managed:X.X.X -->` marker but does **not** migrate — that's `/memex:upgrade`'s job.

## What init does on old-version detection

1. Surface the version mismatch ("Workspace is on Memex `<old>`; current is `<current>`.").
2. Tell the user to run `/memex:upgrade` to migrate.
3. Stop. Init does not modify the workspace beyond this notice.

## Why init delegates instead of migrating in-place

`/memex:upgrade` is the orchestrator for `/memex:resummarize` + `/memex:reindex` + `/memex:lint`. It detects state, sequences the steps correctly (resummarize before reindex), and is idempotent on re-run. Init duplicating that logic would drift over time.

## What changed across versions

For the v1 → v2 changes specifically — closets pagination, typed-field `_CLOSETS.md`, summary-format-version `2`, temporal facts sidecar, typed-edge graph — see `memex/skills/upgrade/references/v1-to-v2.md`.

Future major versions add their own playbooks under that directory. Init's role is just to point users at the right tool.
