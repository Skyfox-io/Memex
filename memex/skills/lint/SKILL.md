---
name: lint
description: >
  Audit workspace structural health: stale status, orphan files/folders, unannotated
  decision supersessions, manifest drift. Read-only; `--fix` applies safe annotations.
  Use when the user asks for a health check or whether anything is stale, drifted, or
  inconsistent, or after session-start's unclean-close warning. Don't fire on vague
  unease or as a routine session step -- session-start/session-end handle hygiene.
  Wikilink targets: `/memex:wikilinks` (lint doesn't re-scan links).
argument-hint: "[--fix]"
---

# Memex - Lint

**Wikilink rule:** Use `[[filename]]` for every file reference in markdown.

Audit drift and structural integrity, read-only by default. Nine checks, one report.

---

## Step 1: Detect workspace

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash, then check for `_MANIFEST.md`: missing -- "Memex is not initialized. Run `/memex:init` first." Stop. Present (with or without `<!-- memex-managed` marker) -- continue.

---

## Step 2: Read manifest

Parse `_MANIFEST.md`: Tier 1 table (always-loaded files), Tier 2 sections (domain hub references), Tier 3 table (archived files), Hub Map (domain-to-hub mapping).

Resolve paths via: config table (if present) > convention (`memory/`) > search.

---

## Step 3: Run checks

Run checks in order, collecting `WARN` (actionable) or `INFO` (observational) findings.

### 3.1 Status Freshness

Read `status.md`'s `Last updated: YYYY-MM-DD` line.

- **WARN** if more than 3 days old (include exact date and day count).
- **PASS** if 3 days or fewer.
- **WARN** if no `Last updated` line at all.

### 3.2 Decision Consistency

Read `decisions.md` in full. Scan newer entries for override language referencing earlier entries:

> supersedes, replaces, dropped, no longer, instead of, reverses, overrides

Flag each match whose referenced older entry isn't annotated with `~~strikethrough~~`.

- **WARN** for each unannotated superseded entry. Include both old and new text.
- **PASS** if no unannotated contradictions found.

Only flag explicit override relationships -- don't infer contradictions from topical similarity.

### 3.3 Orphan Files

For each domain in the Hub Map:

1. Source of truth for the domain:
   - **Closets-only hub** (v2.1+): parse `<hub-folder>/_CLOSETS.md`'s `## [[stem]]` headings as registered members.
   - **Legacy hub** (with `[domain]-index.md`): registered = union of the file table's `[[wikilinks]]` and closets entries.
2. List all `.md` files on disk in that domain's folder, excluding the hub index (if any), `_CLOSETS.md`, and `_CLOSETS-archive.md`.
3. Compare.

- **WARN** for each file on disk not registered in closets (or hub table for legacy hubs).
- **INFO** for each registered entry pointing to a missing file.
- **PASS** if all files match.

Skip `memory/`, `scratch/` -- Tier 1, managed by manifest, not hubs.

### 3.3a Orphan Folders

For each workspace-root subdirectory, skip: known infrastructure paths (`.git`, `.claude`, `.obsidian`, `.memex`, `memex`, `node_modules`, `__pycache__`, `.venv`, `venv`, `dist`, `build`); known Memex folders (`memory`, `scratch`); existing hub folders (any Hub Map row's wikilink resolves into it); folders with zero `.md` files. Whatever's left is an orphan folder.

- **WARN** for each orphan folder. Include file count and a one-line topic guess based on file contents.
- **PASS** if no orphan folders.

### 3.4 Stale Blockers

Read `status.md`'s `## Blocked` (or `## What's Blocked`) section; for each item, count sessions in `session-log.md` (all entries) mentioning the blocker text or close paraphrases, unresolved.

- **WARN** if a blocker appears unchanged across ≥ 3 session-log entries OR has been present > 7 days based on session dates.
- **PASS** if no stale blockers, or `Blocked` is empty / says "None".

### 3.5 Closets Coverage

For each `[[*-index]]` row in the Hub Map, check whether `<hub-folder>/_CLOSETS.md` exists; also check `memory/_CLOSETS.md`.

- **WARN** for each hub missing `_CLOSETS.md`.
- **WARN** if `memory/_CLOSETS.md` is missing on a `memex-managed:2.1.x` or newer workspace.
- **PASS** if every hub plus memory has closets.

Skip without a `<!-- memex-managed` marker (compatible mode predates v2); also skip the memory/ check pre-2.1 (Tier 1 closets shipped in 2.1.0).

### 3.6 Typed-Edge Graph Integrity

Run `${CLAUDE_SKILL_DIR}/scripts/extract-graph.py --check`; it exits 1 with a dangling-edge list if any typed-edge frontmatter (`supersedes`, `superseded-by`, `blocks`, `blocked-by`, `people`, `projects`) targets a missing file.

- **WARN** for each dangling edge: `[[source]] <edge-type> → [[target]] (target file not found)`.
- **PASS** if no dangling edges, script unavailable (opt-in -- see Gotchas), or no files have frontmatter.

### 3.7 Summary Format Version

Read `<!-- summary-format-version:N -->` from `_MANIFEST.md`.

- **PASS** if marker says `2`.
- **WARN** if missing or lower.

Skip without a `<!-- memex-managed` marker (compatible mode).

### 3.8 Manifest Consistency

Verify each Hub Map, Tier 1, and Tier 3 row's file exists on disk.

- **WARN** for each missing Hub Map or Tier 1 entry.
- **INFO** for each missing Tier 3 entry (lower priority -- archived).
- **PASS** if all referenced files exist.

---

## Step 4: Emit the report

Exact layout:

```
Memex Health Report

STATUS FRESHNESS: [PASS / N issues]
  [WARN] status.md is [N] days stale (last updated [date]) -- fix: run /memex:update
  ...

DECISION CONSISTENCY: [PASS / N issues]
  [WARN] Entry "[date] - [text]" superseded by "[date] - [text]" but not annotated -- fix: add ~~strikethrough~~ and (superseded [date])
  ...

ORPHAN FILES: [PASS / N issues]
  [WARN] [domain]/[file.md] exists on disk but not registered in _CLOSETS.md (or hub table) -- fix: add via /memex:reindex or /memex:archive
  [INFO] [[file]] registered but not found on disk -- fix: remove from closets/hub
  ...

ORPHAN FOLDERS: [PASS / N issues]
  [WARN] [folder]/ ([N] markdown files, appears to be about [topic]) -- fix: /memex:add-domain [name] or move files into an existing domain
  ...

STALE BLOCKERS: [PASS / N issues]
  [WARN] Blocker "[text]" unchanged for [N] days across [N] sessions -- fix: resolve or update in status.md
  ...

CLOSETS COVERAGE: [PASS / N issues]
  [WARN] Hub [[hub-name]] is missing _CLOSETS.md -- fix: run /memex:reindex
  ...

TYPED-EDGE GRAPH: [PASS / N issues]
  [WARN] [[source]] `<edge-type>` → [[target]] (target file not found) -- fix: create target file or remove frontmatter reference
  ...

SUMMARY FORMAT VERSION: [PASS / N issues]
  [WARN] Manifest summary-format-version is v1 (or missing) -- fix: run /memex:resummarize to upgrade
  ...

MANIFEST CONSISTENCY: [PASS / N issues]
  [WARN] Hub [[hub-name]] listed in Hub Map but file not found on disk -- fix: create hub or remove from map
  [WARN] Tier 1 file [[name]] not found on disk -- fix: create file or remove from manifest
  ...

Summary: [N] warnings, [M] info across 9 checks
```

If a category has no findings, the body collapses to a single `PASS` line.

If all checks pass:

```
Memex Health Report

All checks passed. Workspace is clean.
```

---

## Step 5: Suggested next actions footer

Below the report (skip if all checks PASS), append:

```
Suggested next actions:
  • [if SUMMARY FORMAT VERSION failed] Run /memex:resummarize to upgrade summaries.
  • [if CLOSETS COVERAGE failed] Run /memex:reindex to backfill _CLOSETS.md files.
  • [if SUMMARY FORMAT VERSION and CLOSETS COVERAGE both failed] Run /memex:upgrade to do both in sequence.
  • [if DECISION CONSISTENCY failed] Run /memex:lint --fix to annotate superseded decisions.
  • [if ORPHAN FILES has dangling registered entries (INFO)] Run /memex:lint --fix to remove dead closets/hub entries.
  • [if ORPHAN FOLDERS failed] Run /memex:add-domain <name> for each orphan folder, or move its files into an existing domain.
  • [if TYPED-EDGE GRAPH failed] Open the source file and fix or remove the dangling frontmatter reference. Run /memex:reindex to regenerate memory/.graph.md once edges resolve.
  • [if STATUS FRESHNESS failed] Run /memex:update to refresh status.md.
  • [if STALE BLOCKERS failed] Edit status.md to resolve or restate the blocker.
  • [if any wikilink targets in the workspace look broken outside lint's scope] Run /memex:wikilinks to verify [[link]] integrity (lint does not check link targets).
  • [if anything else looks like long-standing drift] Run /memex:consolidate for a deeper sweep (dedup, decisions contradictions, orphans, decisions compression).
```

Include only lines whose check failed; omit the section entirely if everything passed.

---

## Step 6: Apply fixes (only if `--fix` or user confirms)

**Safe fixes -- apply without per-item confirmation:**

- Annotate superseded decisions with `~~strikethrough~~` and date pointers.
- Remove hub entries pointing to files no longer on disk.
- Update manifest entries for missing summaries.

**Destructive fixes -- confirm each one individually:**

- Remove orphan files from disk.
- Remove Tier 1 entries for files that don't exist.

After applying fixes, re-run all nine checks and emit an updated report. If fixes weren't requested, stop after Step 5 -- do not prompt.

---

## Gotchas

- **`--fix` arrives via `$ARGUMENTS`**; without it lint never writes (see Step 6).
- **Orphan = unregistered in closets** (or hub table, legacy) -- inbound wikilinks don't exempt a file; closets are authoritative in v2.1+.
- **3.3/3.3a are independent, both run every lint** -- FILES scans known hub folders' contents; FOLDERS finds folders missing from the Hub Map entirely.
- **Supersede detection is keyword-based** -- flags only literal "supersedes/replaces/dropped/no longer/instead of/reverses/overrides"; false negatives over false positives by design.
- **A missing `extract-graph.py` passes the graph check silently** (typed edges are opt-in) -- don't read PASS as proof the graph is healthy unless the script ran.
- **Stale-blocker check needs `session-log.md`** -- missing/empty log means blockers can't be aged; passes by default -- not "no stale blockers".
- **Compatible-mode skip (3.5/3.7)** -- no `<!-- memex-managed` marker means pre-v2; skipping avoids nagging about conventions it never adopted.
- **Next-action suggestions are advisory** -- lint never auto-runs `/memex:reindex`, `/memex:resummarize`, or `/memex:consolidate`.
