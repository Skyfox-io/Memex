---
name: session-end
description: >
  Use when closing a Memex session: at the SessionEnd hook, when a session is about to
  time out, when the hook didn't fire, or to force a clean checkpoint before a long break.
  Updates status.md, appends session-log entry, refreshes hub summaries and touched
  `_CLOSETS.md` entries, verifies wikilinks, scopes a wikilink suggest pass to files
  modified this session.
---

# Memex - Session End

**Wikilink rule:** When referencing files in any markdown you write, use `[[filename]]` format. Plain-text filenames break Obsidian graph connectivity.

Leave the workspace in a clean state so the next session starts with current context. Work through each step in order. Don't skip steps. Don't ask for permission between steps. Execute everything and report at the end.

Session-end does work that's *proportional to the session* — touched files, modified hubs, new decisions. Workspace-wide maintenance (typed-edge graph rebuild, deep dedup, contradiction sweep, decisions compression) lives in `/memex:reindex` and `/memex:consolidate` and runs on its own cadence.

---

## Step 1: Detect workspace and resolve paths

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists. If not, skip silently and stop.

If it exists, resolve file paths via this chain (first match wins):

1. Config table in `_MANIFEST.md` (if present)
2. Convention (`memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `scratch/ideas.md` or `ideas.md`)
3. Search by name

There is no session lock. Session-end is unconditional and idempotent.

---

## Step 2: Synthesize the session

Before touching files, write a brief internal summary: files created/modified/moved, domains touched, decisions made, what was completed vs. left open.

---

## Step 3: Update status.md (idempotent)

- Update "Last updated" date to today
- Remove completed items from "What's In Progress"
- Update "What's Blocked". Resolve unblocked items, add new blockers
- Update "Next Priorities" to reflect what actually comes next

**Idempotency check:** Before writing, compute the new content. Strip the "Last updated" line from both old and new, hash both. If hashes match (substance unchanged), skip the write entirely, including the date. This prevents "session-end ran twice" from compounding drift via spurious timestamp churn.

---

## Step 4: Write the session-log entry

Prepend at the top of `session-log.md` (after the header, before existing entries):

```
## YYYY-MM-DD - [one-line title]

- [what changed - name files specifically]
- [decisions made or insights locked]
- [what's next / what was left open]

---
```

3-5 bullets. Past tense. Specific.

If the log has more than 10 entries, archive the oldest:

1. Read `session-log-archive.md` in full. If missing, create it with header `# Session Log - Archive`.
2. Prepend oldest entries above existing archive content. Never overwrite existing entries.
3. If `[[session-log-archive]]` isn't in the Tier 3 table of `_MANIFEST.md`, add it:
   ```
   | [[session-log-archive]] | Older session log entries | YYYY-MM-DD |
   ```

---

## Step 5: Update hub files, manifest summaries, and `_CLOSETS.md`

Only update hubs for domains actually touched this session.

Read the Hub Map to identify each domain's hub. Also scan touched folders for any `*-index.md` file. This catches hubs created informally (without `/memex:add-domain`).

### 5a. Hub-table entries (legacy hubs only)

For each touched hub that has a prose `[domain]-index.md` file with a file table, update the table:

- Add new files with `[[filename]]` wikilinks, a retrieval-tuned summary, and status.
- Update the status of existing entries.
- Every file in a hub table must have a `[[wikilink]]`.

For **closets-only hubs** (v2.1+ default), skip the hub-table step entirely. Closets are the source of truth; new files land in `_CLOSETS.md` via Step 5c.

Always update the one-line summaries in `_MANIFEST.md` if the content of any Tier 1 or Tier 2 file changed meaningfully.

**Summary rules.** See [`references/summary-rules.md`](references/summary-rules.md) for the 8 retrieval-tuned rules, examples, and self-check. The rules govern hub summaries, manifest summaries, and every typed field in `_CLOSETS.md`. Summary content is benchmark-validated (90.1% R@5 on LongMemEval-S). Do not paraphrase rule meanings.

### 5b. Status sections in touched domain files

Scan domain files read or edited this session for status-like sections (`## Status`, `## Current State`, `## Progress`). If this session's work made any of them stale (e.g., status still marked "planned" when work completed; counts/dates that no longer reflect reality), update them.

Only check files actually touched; do not scan the full workspace.

### 5c. Refresh `_CLOSETS.md` for touched hubs

For each touched hub, refresh the per-hub `_CLOSETS.md` (sibling of the hub index, e.g., `programs/_CLOSETS.md`). This is the typed-field index future sessions scan to decide which files to open without reading them all.

**Format, field semantics, pagination policy (30-entry cap), and read-side fallback.** See [`references/closets-format.md`](references/closets-format.md). Read it before touching closets files unless you've already read it this session.

Quick rules: one `## [[stem]]` heading per file; `subjects`/`people`/`claims`/`decisions`/`dates`/`status` lines (omit empty ones); cap each entry at ~1500 chars; only refresh entries for files touched this session; create the file if it doesn't exist for a touched hub.

After refreshing, if `_CLOSETS.md` would exceed 30 entries, follow the pagination policy in the reference (including the Recently Archived section in the primary file).

### 5d. Refresh `memory/_CLOSETS.md`

If any Tier 1 file (`status.md`, `session-log.md`, `decisions.md`, `glossary.md`, plus any user-added Tier 1 entries like `contacts.md`) was touched this session, refresh its entry in `memory/_CLOSETS.md`. Same format as hub closets. No pagination — Tier 1 is a small fixed set.

If `memory/_CLOSETS.md` doesn't exist on a 2.1.x+ workspace, create it from `memory-closets.md.tmpl` and seed entries for every Tier 1 file in the manifest.

### Self-check

Re-read each summary written or updated this session. For each: *if the user asked about each subject named in the file, would this summary surface it in the top 5 manifest hits?* If a subject is missing, add it.

---

## Step 6: Scan for untracked content

Scan the workspace for files and folders not listed in any hub or the manifest. Briefly read content to understand each.

- **Folders with 3+ markdown files not in the Hub Map:** Likely domains. Note folder name, file count, what files appear to be about (based on content, not just filenames).
- **Loose project files not in any hub:** Files at workspace root or in untracked folders that look like project documents. Note which existing domain they'd fit, or if they suggest a new domain.

Build a list for the close-report block. Keep this fast. Session-end *surfaces* untracked content; deep dedup and contradiction sweeps are `/memex:consolidate`'s job.

---

## Step 7: Log decisions

If this session produced meaningful decisions, append to `decisions.md`:

```
**YYYY-MM-DD** - [decision stated as a fact, one sentence]
```

Append-only. Session-end does **not** compress. If after appending `decisions.md` is at or above 95 lines, surface a one-line nudge in the close report: "decisions.md at <N> lines; run `/memex:consolidate --fix` to compress." Do not block close on it.

Skip this step if no decisions were made.

---

## Step 8: Verify wikilinks (broken + scoped suggest)

### 8a. Wikilink integrity

Run the script at `${CLAUDE_SKILL_DIR}/scripts/verify-wikilinks.py` against the workspace, passing `--skip .claude .obsidian .git` plus any scratch directory path:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/verify-wikilinks.py" "$WORKSPACE_ROOT" --skip .claude .obsidian .git
```

If the script can't be found, report "Wikilink script not found - skipping." Do not silently pass.

If broken links are found, fix them. Target is always zero.

### 8b. Wikilink suggest (scoped to this session)

If any markdown files were created or modified this session (from Step 2's internal summary), run a scoped suggest pass to catch new plain-text references that should be wikilinks:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/verify-wikilinks.py" "$WORKSPACE_ROOT" --suggest --files <file1> <file2> ... --skip .claude .obsidian .git
```

If the suggest pass returns hits, surface them in the close report. Apply automatically only for unambiguous matches (the suggested wikilink stem and the plain-text match are an exact case-fold match for an existing file). For any ambiguous hits (short stems, multiple candidate targets), list them and let the user route.

If no files were touched, skip 8b.

This is the proportional version of `/memex:wikilinks --suggest` (workspace-wide). Run that on demand for periodic full sweeps.

### 8c. Typed-edge graph (deferred)

The typed-edge graph is no longer rebuilt at session-end. It refreshes lazily via `/memex:reindex` and `/memex:consolidate`, which both run `extract-graph.py` against the workspace. If a frontmatter-bearing file was touched this session and dangling edges matter, mention it in the close report:

> `frontmatter touched this session — run /memex:consolidate or /memex:reindex to refresh memory/.graph.md`

This is informational. Don't block close on it.

### 8d. Self-test

Verify each prior step's output landed:

- `status.md`. "Last updated" is today (or unchanged if Step 3 was idempotent-skipped).
- `session-log.md`. New entry at top with today's date.
- Hub files for touched domains (legacy hubs only). List every file added or modified.
- `_CLOSETS.md` for touched hubs and `memory/_CLOSETS.md` for touched Tier 1 files. Entry for every file touched.
- `_MANIFEST.md`. Summary-format-version marker still says `:2`.
- Wikilink check. Exited with status 0 (CLEAN).

If any check fails, surface in Step 9 as `[INCOMPLETE]` next to the failed step. Drift is louder than silence.

---

## Step 9: Confirm close

Output:

```
Session closed.

status.md - updated [date]
session-log.md - entry added: "[session title]"
Hub updates: [list or "none needed"]
Decisions logged: [count or "none"]
Wikilinks: CLEAN

Next session: [top priority from status.md]
```

If Step 6 found untracked content, append:

```
Untracked content:
  [folder]/ ([count] files about [topic]) - /memex:add-domain [name]
  [file.md] (fits in [domain]/) - say "organize files" to move it
```

If the ideas inbox has items with suggested routes, append:

```
Ideas inbox: [count] items
  "[title]" -> [domain]. Say "route ideas" to move ready items.
```

### Consolidate cadence nag

Read the most recent line of `memory/.consolidate-runs.log` if it exists. Compute days between that timestamp and today.

Suppression: skip the nag entirely if the workspace is < 14 days old (check `_MANIFEST.md` mtime). New workspaces have no drift to sweep yet, and a "never run" message on every session-end is just noise.

Otherwise:

- If the log is missing OR the last run was > 14 days ago: append `Last /memex:consolidate: [N days ago | never]. Consider running it for a deeper drift sweep.` to the close report.
- Otherwise: omit.

This is a one-line nudge, not a hard requirement.

Informational. Session is closed. Do not block on a response.

---

## Step 10: Write session-close marker

If `$CLAUDE_PLUGIN_DATA` is set and the directory exists, append to `$CLAUDE_PLUGIN_DATA/session-closes.log`:

```
YYYY-MM-DDTHH:MM:SS  workspace-root-basename  clean
```

Best-effort; never blocks close. There's no lock to clear — session-start/session-end are stateless.

---

## Wikilink rules during session-end

- Every file reference in a hub table uses `[[filename]]` format.
- Every new file added to a hub gets a `[[wikilink]]`.
- If a file was renamed or moved this session, search for `[[old-name]]` across all `.md` files and update to `[[new-name]]`.

---

## Gotchas

- **Session-end is the most common victim of session timeouts.** If it dies mid-execution, partial updates may have been written. Session-start detects this by comparing `status.md` mtime to the most recent workspace mtime (no lock file involved). If you suspect drift, run `/memex:lint`.
- **There is no session lock.** v2.1+ removed `memory/.session.lock` entirely. Session-end runs unconditionally and is fully idempotent (Step 3 hashes substance to skip no-op writes). Bulk-write skills (`/memex:reindex`, `/memex:consolidate`, `/memex:resummarize`, `/memex:upgrade`) keep their own locks for actual concurrency reasons.
- **Typed-edge graph is rebuilt by reindex/consolidate, not session-end.** If a frontmatter-bearing file changed this session, the close report nudges to run one of those skills. The graph is purely additive and regenerable; a one-session lag has no retrieval impact.
- **Idempotency is intentional** (Step 3). If your run produces a no-op status.md write, that's correct, not a bug. Don't "fix" it by forcing a date refresh.
- **The 30-entry closets cap is a hard load-time budget**, not a soft preference. Do not let `_CLOSETS.md` grow past 30; route overflow to `_CLOSETS-archive.md` per the pagination policy in [`references/closets-format.md`](references/closets-format.md).
- **Hub files created informally** (user manually creates `research/research-index.md` instead of using `/memex:add-domain`) are detected in Step 5 by scanning for `*-index.md` files in *touched* folders. Hubs in untouched folders won't be found until a future session touches that domain.
- **Decisions.md is append-only at session-end.** Compression lives in `/memex:consolidate`. If the file is approaching its 100-line cap, the close report nudges; it doesn't compress in-line.
- **Summary content is benchmark-validated**, not stylistic preference. Summaries that drop verbatim user-stated facts ("allergic to coffee" → "has dietary restrictions") measurably tank R@5. Follow [`references/summary-rules.md`](references/summary-rules.md) literally.
- **Closets archive is not loaded eagerly.** Session-start only reads `_CLOSETS.md`; the archive is the fallback. Don't move recently active files to the archive; pagination sorts by underlying-file mtime for a reason.
