# v2.0 → v2.1 upgrade playbook

> Referenced from `/memex:upgrade` when the manifest marker is `2.0.x` or older with summary-format-version 2.

## What changes in v2.1

- **`memory/_CLOSETS.md`.** Tier 1 files (status, session-log, decisions, glossary, contacts) now have a typed-field index. Field-level retrieval ("who is Mike?", "what did the user say about X?") hits structured fields instead of scanning full files.
- **Hub indexes are optional.** Domains can register with just a `_CLOSETS.md`, no prose `[domain]-index.md` required. Existing index files keep working; new domains scaffold without them by default.
- **Recently Archived section.** When a hub's primary `_CLOSETS.md` paginates, it now appends a list of the 5 most recently demoted files so the archive isn't invisible.
- **Lighter session lifecycle.** Session-end no longer rebuilds the typed-edge graph; that runs lazily via `/memex:reindex` and `/memex:consolidate`. The session lock (`memory/.session.lock`) is removed entirely; unclean-close detection is mtime-based.
- **Decisions compression in `/memex:consolidate`.** Session-end is append-only for decisions; compression rules (drop redundant supersession pairs, collapse same-period clusters) live in consolidate.
- **`/memex:lint` adds an ORPHAN FOLDERS check.** Top-level directories with markdown files but no Hub Map registration get flagged.
- **`/memex:search`.** New skill for cross-hub queries within a single workspace (companion to `/memex:cross-search`, which spans linked workspaces).

## Upgrade actions

| Workspace state | Action |
|---|---|
| `memory/_CLOSETS.md` missing | `/memex:reindex --hub memory` |
| Manifest `<!-- memex-managed:2.0.x -->` | bump marker to `2.1.0` after other steps complete |
| Workspace has hub indexes that are pure file-tables | optional: dissolve them; the closets file becomes the source of truth |

## What does *not* change

- All v2.0 workspaces remain fully functional. Hub indexes keep working. Closets format 1.1 stays current. Summary format 2 stays current. The typed-edge graph format is unchanged.
- Every existing closets file is forward-compatible. v2.1 adds the optional Recently Archived section on next pagination; existing primary entries are not rewritten.
- `/memex:cross-search` is unchanged. `/memex:search` is the new within-workspace companion.

## Idempotency

`/memex:upgrade` is a no-op on a workspace that's already at 2.1.0 (no marker bump, no reindex). The state-detection in Step 1 catches that.
