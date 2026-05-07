---
name: init
description: >
  Set up Memex in the current workspace. Use when the user says "initialize memex",
  "set up memex here", or runs /memex:init in a fresh repo, an existing repo with
  loose markdown, a workspace with a foreign manifest, or one with an outdated Memex
  version marker. Detects state and runs scaffold, scan-and-organize, migrate, or
  health-check accordingly.
disable-model-invocation: true
---

# Memex - Init

**Wikilink rule:** When referencing any file in markdown you write or edit, always use `[[filename]]` wikilink format. Never plain text.

**Core principle: never assume, never delete.** Existing files are sacred. Moves only happen with explicit confirmation.

---

## Step 1: Detect workspace state

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

| State | Detection | Action |
|-------|-----------|--------|
| Empty | No markdown files, no manifest | Quick Start (below) |
| Files, no manifest | Markdown exists, no `_MANIFEST.md` | See `references/scan-and-organize.md` |
| Compatible manifest | `_MANIFEST.md` exists, no `<!-- memex-managed` marker | Offer to add marker (opt in) or continue compatible |
| Old version | `<!-- memex-managed:X.X.X -->` behind current | Tell the user to run `/memex:upgrade` (one-command migration to current version). Init does not perform the migration itself — see `references/migrations.md` for what changes. |
| Current version | Current marker | See `references/health-check.md` |

Do not announce the detected state. Just run the appropriate flow.

---

## Quick Start (empty workspace)

1. Ask: **"What are you working on right now?"** — seeds `status.md` with active focus, in-progress items, next priorities.
2. Create from `templates/`: `memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `memory/glossary.md`, `scratch/ideas.md`.
3. Append the three Memex lines to workspace-root `CLAUDE.md` (template at `templates/CLAUDE.md.tmpl`). Preserve existing content. Skip if `.claude/CLAUDE.md` already has them.
4. Create `_MANIFEST.md` from `templates/_MANIFEST.md.tmpl` — Tier 1 table, empty Tier 2/3, empty Hub Map. **Write last** — it's the activation marker.
5. Print the post-setup message in `references/post-setup-message.md`.

---

## Scan and Organize (existing files)

See `references/scan-and-organize.md` for the full scan / analyze / propose / build flow. Closets file format is canonical at `memex/skills/session-end/references/closets-format.md`; per-entry summary fields follow `memex/skills/session-end/references/summary-rules.md`.

---

## Health Check (current Memex workspace)

See `references/health-check.md`.

---

## Migrations (old version marker)

See `references/migrations.md`. For a one-command v1→v2 upgrade that orchestrates `/memex:resummarize` + `/memex:reindex` + lint, prefer `/memex:upgrade`.

---

## Wikilink Rules

- Every file reference in a hub table or `_MANIFEST.md` uses `[[filename]]`.
- When moving a file, search `.md` files for `[[old-name]]` and update to `[[new-name]]`.
- After all writes, run wikilink verification — must be CLEAN.

---

## Gotchas

- **Foreign session hooks in root `CLAUDE.md`.** If another plugin already owns session-start/session-end, ask which plugin should own the lifecycle. Don't silently overwrite.
- **`.claude/CLAUDE.md` is platform-managed.** Always target the workspace-root `CLAUDE.md`, never `.claude/CLAUDE.md`.
- **Manifest is the activation marker — write it last.** A partial scaffold without `_MANIFEST.md` is recoverable; a manifest pointing at files that don't exist will break session-start.
- **Catch-all folders are not domains.** A `notes/` folder with meeting notes + ideas + decisions mixed together should be dissolved file-by-file, not turned into a `notes-index.md` hub.
- **Wikilink conversion false-positives on short stems.** `api.md` will match every "API" in prose. Pass 1 (automated) only does exact filename or hyphen-to-space matches; Pass 2 (semantic) requires user confirmation. Don't merge them.
- **Conflicting files are surfaced, not merged.** If two files cover the same topic with different content, ask which is authoritative before placing either. Silent merge loses information.
- **Stale files route to Tier 3, not active domains.** Markers like `outdated`, `deprecated`, `superseded`, `v1` (when v2 exists) — these go straight to archive, even if their topic matches an active domain.

---

## Rules

- Never delete user files. Moves require confirmation. Originals of migrated files go to Tier 3.
- No placeholder text in saved files.
- Manifest writes last.
- Always ask what the user is working on. Seed `status.md` with the answer.
- Wikilink conversion is two passes. Pass 1 automated, Pass 2 proposed.
- Manifest summaries: every file entry gets a one-line content summary so session-start can scan without opening files.
- Batch writes when files don't depend on each other.
