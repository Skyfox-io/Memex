---
name: session-end
description: >
  Use when closing a Memex session: at the SessionEnd hook, when a session is about to
  time out, when the hook didn't fire, or to force a clean checkpoint before a long break.
  Updates status.md, appends session-log entry, refreshes hub summaries and per-hub
  `_CLOSETS.md`, verifies wikilinks, refreshes typed-edge graph, clears the session lock.
---

# Memex - Session End

**Wikilink rule:** when referencing files in any markdown you write, use `[[filename]]` format. Plain-text filenames break Obsidian graph connectivity.

Leave the workspace in a clean, fully updated state so the next session starts with perfect context. Work through each step in order. Don't skip steps. Don't ask for permission between steps — execute everything and report at the end.

---

## Step 1: Detect workspace, resolve paths, take session lock

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists. If not, skip silently and stop.

If it exists, resolve file paths via this chain (first match wins):

1. Config table in `_MANIFEST.md` (if present)
2. Convention (`memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `scratch/ideas.md` or `ideas.md`)
3. Search by name

### Session lock

Check `memory/.session.lock` (created by session-start, cleared by session-end on clean close):

- **Lock present, matches active session:** proceed.
- **Lock present, timestamp ≥ 24 hours old:** previous session likely crashed. Continue, but flag in the close report: "Previous session lock was stale (created [timestamp]). Drift may have accumulated. Consider running `/memex:lint` after this close."
- **Lock missing:** session-start was skipped or interrupted. Continue with the same flag.

Step 10 clears the lock after a successful close.

---

## Step 2: Synthesize the session

Before touching files, write a brief internal summary: files created/modified/moved, domains touched, decisions made, what was completed vs. left open.

---

## Step 3: Update status.md (idempotent)

- Update "Last updated" date to today
- Remove completed items from "What's In Progress"
- Update "What's Blocked" — resolve unblocked items, add new blockers
- Update "Next Priorities" to reflect what actually comes next

**Idempotency check:** before writing, compute the new content. Strip the "Last updated" line from both old and new, hash both. If hashes match (substance unchanged), skip the write entirely — including the date. This prevents "session-end ran twice" from compounding drift via spurious timestamp churn.

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

Read the Hub Map to identify each domain's hub. Also scan touched folders for any `*-index.md` file — this catches hubs created informally (without `/memex:add-domain`).

### 5a. Hub-table entries

For each touched hub:

- Add new files with `[[filename]]` wikilinks, a retrieval-tuned summary, and status.
- Update the status of existing entries.
- Every file in a hub table must have a `[[wikilink]]`.

Also update the one-line summaries in `_MANIFEST.md` if the content of any Tier 1 or Tier 2 file changed meaningfully.

**Summary rules** — see [`references/summary-rules.md`](references/summary-rules.md) for the 8 retrieval-tuned rules, examples, and self-check. The rules govern hub summaries, manifest summaries, and every typed field in `_CLOSETS.md`. Summary content is benchmark-validated (90.1% R@5 on LongMemEval-S) — do not paraphrase rule meanings.

### 5b. Status sections in touched domain files

Scan domain files read or edited this session for status-like sections (`## Status`, `## Current State`, `## Progress`). If this session's work made any of them stale (e.g., status still marked "planned" when work completed; counts/dates that no longer reflect reality), update them.

Only check files actually touched; do not scan the full workspace.

### 5c. Refresh `_CLOSETS.md` for touched hubs

For each touched hub, refresh the per-hub `_CLOSETS.md` (sibling of the hub index, e.g., `programs/_CLOSETS.md`). This is the typed-field index future sessions scan to decide which files to open without reading them all.

**Format, field semantics, pagination policy (30-entry cap), and read-side fallback** — see [`references/closets-format.md`](references/closets-format.md). Read it before touching closets files unless you've already read it this session.

Quick rules: one `## [[stem]]` heading per file; `subjects`/`people`/`claims`/`decisions`/`dates`/`status` lines (omit empty ones); cap each entry at ~1500 chars; only refresh entries for files touched this session; create the file if it doesn't exist for a touched hub.

After refreshing, if `_CLOSETS.md` would exceed 30 entries, follow the pagination policy in the reference.

### Self-check

Re-read each summary written or updated this session. For each: *if the user asked about each subject named in the file, would this summary surface it in the top 5 manifest hits?* If a subject is missing, add it.

---

## Step 6: Scan for untracked content

Scan the workspace for files and folders not listed in any hub or the manifest. Briefly read content to understand each.

- **Folders with 3+ markdown files not in the Hub Map:** likely domains. Note folder name, file count, what files appear to be about (based on content, not just filenames).
- **Loose project files not in any hub:** files at workspace root or in untracked folders that look like project documents. Note which existing domain they'd fit, or if they suggest a new domain.

Build a list for the close-report block. Keep this fast — session-end *surfaces* untracked content; deep dedup and contradiction sweeps are `/memex:consolidate`'s job.

---

## Step 7: Log decisions

If this session produced meaningful decisions, append to `decisions.md`:

```
**YYYY-MM-DD** - [decision stated as a fact, one sentence]
```

If `decisions.md` is approaching 100 lines, compress related entries from the same time period into summary entries. Don't just truncate. Keep the file under 100 lines. Skip this step if no decisions were made.

---

## Step 8: Verify wikilinks and refresh typed-edge graph

### 8a. Wikilink integrity

Resolve the script path:

1. `${CLAUDE_PLUGIN_ROOT}/scripts/verify-wikilinks.py` (if set)
2. `${CLAUDE_SKILL_DIR}/../../scripts/verify-wikilinks.py` (fallback)

Pass `--skip .claude .obsidian .git` plus any scratch directory path.

If the script can't be found, report "Wikilink script not found - skipping." Do not silently pass.

If broken links are found, fix them. Target is always zero.

### 8b. Typed-edge graph

If any file with YAML frontmatter was created or modified this session, refresh the graph:

1. Resolve `${CLAUDE_PLUGIN_ROOT}/scripts/extract-graph.py` (or the `${CLAUDE_SKILL_DIR}/../../scripts/extract-graph.py` fallback).
2. Run with the workspace path. It writes `memory/.graph.md`.
3. The script reports dangling edges (typed references to nonexistent files). List them in the close report so the user can resolve.

If no frontmatter-bearing files were touched, skip 8b — the graph is unchanged.

The graph is purely additive; files without frontmatter contribute no edges. See `ARCHITECTURE.md` "Typed Edges" for supported keys.

### 8c. Self-test

Verify each prior step's output landed:

- `status.md` — "Last updated" is today (or unchanged if Step 3 was idempotent-skipped).
- `session-log.md` — new entry at top with today's date.
- Hub files for touched domains — list every file added or modified.
- `_CLOSETS.md` for touched hubs — entry for every file touched.
- `_MANIFEST.md` — summary-format-version marker still says `:2`.
- Wikilink check — exited with status 0 (CLEAN).

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

## Step 10: Write session marker and clear lock

If `$CLAUDE_PLUGIN_DATA` is set and the directory exists, append to `$CLAUDE_PLUGIN_DATA/session-closes.log`:

```
YYYY-MM-DDTHH:MM:SS  workspace-root-basename  clean
```

Then remove `memory/.session.lock` if it exists. This signals to the next session-start that this session closed cleanly.

If `$CLAUDE_PLUGIN_DATA` isn't set, skip the marker but still clear the lock. Both are best-effort and never block close.

---

## Wikilink rules during session-end

- Every file reference in a hub table uses `[[filename]]` format.
- Every new file added to a hub gets a `[[wikilink]]`.
- If a file was renamed or moved this session, search for `[[old-name]]` across all `.md` files and update to `[[new-name]]`.

---

## Gotchas

- **Session-end is the most common victim of session timeouts.** If it dies mid-execution, partial updates may have been written. Session-start's staleness warning catches this case — but if you suspect drift, run `/memex:lint`.
- **Idempotency is intentional** (Step 3). If your run produces a no-op status.md write, that's correct, not a bug. Don't "fix" it by forcing a date refresh.
- **The 30-entry closets cap is a hard load-time budget**, not a soft preference. Do not let `_CLOSETS.md` grow past 30; route overflow to `_CLOSETS-archive.md` per the pagination policy in [`references/closets-format.md`](references/closets-format.md).
- **Hub files created informally** (user manually creates `research/research-index.md` instead of using `/memex:add-domain`) are detected in Step 5 by scanning for `*-index.md` files in *touched* folders. Hubs in untouched folders won't be found until a future session touches that domain.
- **Decisions.md compression** (Step 7): merge entries from the same time period that cover the same topic. Don't truncate — that loses retrieval signal.
- **Summary content is benchmark-validated**, not stylistic preference. Summaries that drop verbatim user-stated facts ("allergic to coffee" → "has dietary restrictions") measurably tank R@5. Follow [`references/summary-rules.md`](references/summary-rules.md) literally.
- **Closets archive is not loaded eagerly.** Session-start only reads `_CLOSETS.md`; the archive is the fallback. Don't move recently active files to the archive; pagination sorts by underlying-file mtime for a reason.
