---
name: lint
description: >
  Audit workspace structural health -- stale status.md, unannotated superseded decisions,
  orphan files (on disk but not in any hub), stale blockers, dangling typed edges, manifest
  drift, missing `_CLOSETS.md`, outdated summary-format version. Read-only by default; `--fix`
  applies safe annotations. Trigger after returning from a break, before a milestone or release,
  when something feels out of sync, when status/decisions look stale, or when the user asks
  "is this workspace healthy". For wikilink integrity specifically, use `/memex:wikilinks`
  -- lint does not re-scan link targets.
argument-hint: "[--fix]"
---

# Memex - Lint

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Audit semantic drift and structural integrity. Read-only by default. Eight checks, one report.

---

## Step 1: Detect workspace

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists at the workspace root.

- **No manifest:** "Memex is not initialized. Run `/memex:init` first." Stop.
- **Manifest exists** (with or without `<!-- memex-managed` marker): Continue.

---

## Step 2: Read manifest

Read `_MANIFEST.md`. Parse:

- **Tier 1 table** -- always-loaded files with paths
- **Tier 2 sections** -- domain sections with hub references
- **Tier 3 table** -- archived files
- **Hub Map** -- domain-to-hub mapping

Resolve paths via: Config table (if present) > convention (`memory/`) > search.

---

## Step 3: Run checks

Execute each check in order. Collect findings as `WARN` (actionable) or `INFO` (observational).

### 3.1 Status Freshness

Read `status.md`. Parse the `Last updated: YYYY-MM-DD` line.

- **WARN** if more than 3 days old. Include the exact date and day count.
- **PASS** if 3 days or fewer.
- **WARN** if no `Last updated` line at all.

### 3.2 Decision Consistency

Read `decisions.md` in full. Scan newer entries for override language referencing earlier entries:

> supersedes, replaces, dropped, no longer, instead of, reverses, overrides

For each match, check whether the older entry being referenced is annotated with `~~strikethrough~~`.

- **WARN** for each unannotated superseded entry. Include both old and new text.
- **PASS** if no unannotated contradictions found.

Do not infer contradictions from topical similarity. Only flag entries where the override relationship is explicit.

### 3.3 Orphan Files

For each domain in the Hub Map:

1. Determine the source of truth for the domain:
   - **Closets-only hub** (v2.1+): `<hub-folder>/_CLOSETS.md`. Parse `## [[stem]]` headings; those are the registered members.
   - **Legacy hub** (with `[domain]-index.md`): parse the hub's file table for `[[wikilinks]]`. Treat the union of table entries and closets entries as registered.
2. List all `.md` files on disk in that domain's folder, excluding the hub index (if any), `_CLOSETS.md`, and `_CLOSETS-archive.md`.
3. Compare.

- **WARN** for each file on disk not registered in closets (or hub table for legacy hubs).
- **INFO** for each registered entry pointing to a missing file.
- **PASS** if all files match.

Skip `memory/` and `scratch/` -- Tier 1, managed by manifest, not hubs.

### 3.3a Orphan Folders

Scan workspace-root subdirectories. For each subdirectory:

1. Skip if it's a known infrastructure path: `.git`, `.claude`, `.obsidian`, `.memex`, `memex`, `node_modules`, `__pycache__`, `.venv`, `venv`, `dist`, `build`.
2. Skip if it's a known Memex folder: `memory`, `scratch`.
3. Skip if it's already a hub folder (any Hub Map row's wikilink resolves into it).
4. Skip if it contains zero `.md` files.

Whatever's left is an orphan folder.

- **WARN** for each orphan folder. Include file count and a one-line topic guess based on file contents. Suggest: "run `/memex:add-domain <name>` to wire it up."
- **PASS** if no orphan folders.

### 3.4 Stale Blockers

Read `status.md`'s `## Blocked` (or `## What's Blocked`) section. For each item:

1. Read `session-log.md` (all entries).
2. Search for mentions of the blocker text or close paraphrases.
3. Count how many sessions mention it without resolution.

- **WARN** if a blocker appears unchanged across ≥ 3 session-log entries OR has been present > 7 days based on session dates.
- **PASS** if no stale blockers, or `Blocked` is empty / says "None".

### 3.5 Closets Coverage

For each `[[*-index]]` row in the Hub Map, check whether `<hub-folder>/_CLOSETS.md` exists. Also check whether `memory/_CLOSETS.md` exists.

- **WARN** for each hub missing `_CLOSETS.md`. Suggest: "run `/memex:reindex` to backfill."
- **WARN** if `memory/_CLOSETS.md` is missing on a `memex-managed:2.1.x` or newer workspace. Suggest: "run `/memex:reindex --hub memory`."
- **PASS** if every hub plus memory have closets.

Skip if the workspace has no `<!-- memex-managed` marker (compatible mode predates v2). For pre-2.1 workspaces, skip the memory/ check (Tier 1 closets shipped in 2.1.0).

### 3.6 Typed-Edge Graph Integrity

Resolve `extract-graph.py` (`${CLAUDE_PLUGIN_ROOT}/scripts/extract-graph.py` → `${CLAUDE_SKILL_DIR}/../../scripts/extract-graph.py`). Run with `--check` against the workspace. Exits 1 with dangling-edge list if any typed-edge frontmatter (`supersedes`, `superseded-by`, `blocks`, `blocked-by`, `people`, `projects`) targets a missing file.

- **WARN** for each dangling edge: `[[source]] <edge-type> → [[target]] (target file not found)`.
- **PASS** if no dangling edges, OR if the script is unavailable (typed edges are opt-in -- see Gotchas), OR if no files have frontmatter.

### 3.7 Summary Format Version

Read `<!-- summary-format-version:N -->` from `_MANIFEST.md`.

- **PASS** if marker says `2`.
- **WARN** if missing or lower. Suggest: "run `/memex:resummarize` to upgrade summaries to v2."

Skip if the workspace has no `<!-- memex-managed` marker (compatible mode).

### 3.8 Manifest Consistency

For each row in the Hub Map, Tier 1 table, and Tier 3 table, verify the file exists on disk.

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
  • [if TYPED-EDGE GRAPH failed] Open the source file and fix or remove the dangling frontmatter reference. Typed edges are not facts — do not run /memex:facts.
  • [if STATUS FRESHNESS failed] Run /memex:update to refresh status.md.
  • [if STALE BLOCKERS failed] Edit status.md to resolve or restate the blocker.
  • [if any wikilink targets in the workspace look broken outside lint's scope] Run /memex:wikilinks to verify [[link]] integrity (lint does not check link targets).
  • [if anything else looks like long-standing drift, including subject-predicate-object fact contradictions surfaced by /memex:consolidate] Run /memex:consolidate for a deeper sweep (dedup, contradictions, orphans).
```

Only include lines whose triggering check failed. Omit the section entirely if everything passed.

---

## Step 6: Apply fixes (only if `--fix` or user confirms)

**Safe fixes -- apply without per-item confirmation:**

- Annotate superseded decisions with `~~strikethrough~~` and date pointers.
- Remove hub entries pointing to files no longer on disk.
- Update manifest entries for missing summaries.

**Destructive fixes -- confirm each one individually:**

- Remove orphan files from disk.
- Remove Tier 1 entries for files that don't exist.

After applying fixes, re-run all eight checks and emit an updated report.

If the user didn't ask for fixes, stop after Step 5. Do not prompt.

---

## Gotchas

- **Read-only by default.** Without `--fix` (via `$ARGUMENTS`) or explicit user confirmation, never write a file.
- **Not a wikilink checker.** Lint validates manifest/hub/decision structure. Broken `[[link]]` targets are out of scope -- run `/memex:wikilinks`.
- **Orphan = "not registered in closets" (or hub table for legacy hubs).** A file with inbound `[[wikilinks]]` from across the workspace is still an orphan if its hub's closets file doesn't list it. Closets are the source of truth in v2.1+.
- **Orphan folders are folders, not files.** ORPHAN FILES checks files inside known hub folders. ORPHAN FOLDERS checks for hub folders that don't exist in the Hub Map at all (e.g., a `morning-briefs/` directory dropped at workspace root). Both checks run on every lint.
- **Decision-supersede detection is keyword-based.** Only flags when a newer entry literally contains "supersedes/replaces/dropped/no longer/instead of/reverses/overrides". Semantic contradictions without those phrases pass silently. False negatives over false positives by design.
- **`extract-graph.py` missing → graph check passes silently.** Typed edges are opt-in. If the script is unresolvable on both `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}/../../scripts/`, the TYPED-EDGE GRAPH category reports PASS, not WARN. Don't read a passing graph check as proof the graph is healthy unless you've confirmed the script ran.
- **Stale-blocker check needs `session-log.md`.** If session-log is missing or empty, blockers can't be aged. The check passes by default -- don't conflate that with "no stale blockers".
- **Closets coverage check ignores compatible-mode workspaces.** Without a `<!-- memex-managed` marker, the workspace predates v2 conventions; nagging about `_CLOSETS.md` would just spam.
- **Suggested next actions are advisory.** Lint never auto-runs `/memex:reindex`, `/memex:resummarize`, or `/memex:consolidate` -- the footer points at them so the user (or another agent) can decide.
