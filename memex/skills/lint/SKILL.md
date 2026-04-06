---
name: lint
description: >
  Audit workspace health -- stale status, contradicted decisions, orphan files, broken hub refs.
  Run after returning from a break, before a milestone, or when things feel out of sync.
argument-hint: "[--fix]"
disable-model-invocation: true
---

# Memex - Lint

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Audit the workspace for semantic drift and structural issues. Read-only by default.

---

## Step 1: Detect workspace

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists at the workspace root.

- **No manifest:** Tell the user "Memex is not initialized. Run `/memex:init` first." and stop.
- **Manifest exists** (with or without `<!-- memex-managed` marker): Continue.

---

## Step 2: Read manifest

Read `_MANIFEST.md`. Parse:

- **Tier 1 table** -- list of always-loaded files with paths
- **Tier 2 sections** -- domain sections with hub references
- **Tier 3 table** -- archived files
- **Hub Map** -- domain-to-hub mapping

Resolve file paths using: Config table (if present) > convention (`memory/`) > search.

---

## Step 3: Run checks

Read `references/checks.md` for the full check definitions. Execute each check category in order and collect findings. Each finding has a severity (WARN or INFO) and a suggested fix.

---

## Step 4: Report

Output the health report. Exact format:

```
Memex Health Report

STATUS FRESHNESS: [PASS / N issues]
  [WARN] status.md is [N] days stale (last updated [date]) -- fix: run /memex:update
  ...

DECISION CONSISTENCY: [PASS / N issues]
  [WARN] Entry "[date] - [text]" superseded by "[date] - [text]" but not annotated -- fix: add ~~strikethrough~~ and (superseded [date])
  ...

ORPHAN FILES: [PASS / N issues]
  [WARN] [domain]/[file.md] exists on disk but not in [[hub-index]] -- fix: add to hub or /memex:archive
  [INFO] [[file]] listed in [[hub-index]] but not found on disk -- fix: remove from hub
  ...

STALE BLOCKERS: [PASS / N issues]
  [WARN] Blocker "[text]" unchanged for [N] days across [N] sessions -- fix: resolve or update in status.md
  ...

MANIFEST CONSISTENCY: [PASS / N issues]
  [WARN] Hub [[hub-name]] listed in Hub Map but file not found on disk -- fix: create hub or remove from map
  [WARN] Tier 1 file [[name]] not found on disk -- fix: create file or remove from manifest
  ...

Summary: [N] warnings, [M] info across 5 checks
```

If all checks pass:

```
Memex Health Report

All checks passed. Workspace is clean.
```

---

## Step 5: Offer fixes

If the user passed `--fix` via `$ARGUMENTS` or asks to fix issues after seeing the report:

**Safe fixes (apply without per-item confirmation):**
- Annotate superseded decisions with ~~strikethrough~~ and date pointers
- Remove hub entries that point to files that no longer exist on disk
- Update manifest entries for missing summaries

**Destructive fixes (confirm each individually):**
- Remove orphan files from disk
- Remove Tier 1 entries for files that don't exist

After applying fixes, re-run the checks and output an updated report showing what was resolved.

If the user didn't ask for fixes, stop after the report. Do not prompt to fix.

---

## Gotchas

- Lint is read-only by default. The `--fix` flag or explicit user request is required before writing any file.
- Don't duplicate wikilink verification. That's `/memex:wikilinks`. Lint checks structural health, not link integrity.
- Orphan detection uses the manifest and hub files as the source of truth. A file that exists on disk but isn't in any hub is an orphan, even if it has valid wikilinks pointing to it.
- Lint scans domain folders listed in the Hub Map. It does not crawl the entire workspace for unknown folders. Use session-start or session-end for untracked folder detection.
