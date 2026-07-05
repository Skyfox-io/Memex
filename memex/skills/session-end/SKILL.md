---
name: session-end
description: >
  Use when closing a Memex session: at the SessionEnd hook, when a session is about to
  time out, when the hook didn't fire, or to force a clean checkpoint before a long
  break. Updates memory files, refreshes closets, verifies wikilinks.
---

# Memex - Session End

**Wikilink rule:** When referencing files in any markdown you write, use `[[filename]]` format. Plain-text filenames break Obsidian graph connectivity.

Leave the workspace clean for the next session. Work each step in order — no skipping, no asking permission between steps; execute everything, report at the end.

Session-end's work is *proportional to the session* (touched files, modified hubs, new decisions). Workspace-wide maintenance — graph rebuild, dedup, contradiction sweep, decisions compression — lives in `/memex:reindex`/`/memex:consolidate` on their own cadence.

---

## Step 1: Detect workspace and resolve paths

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

No `_MANIFEST.md`: skip silently, stop. Otherwise resolve paths (first match wins): manifest config table → convention (`memory/status.md`, `session-log.md`, `decisions.md`, `scratch/ideas.md` or `ideas.md`) → search by name. No session lock — unconditional and idempotent.

---

## Step 2: Synthesize the session

Before touching files, write a brief internal summary: files created/modified/moved, domains touched, decisions made, done vs. left open.

---

## Step 3: Update status.md (idempotent)

- Update "Last updated" to today
- Remove completed items from "What's In Progress"
- Update "What's Blocked" — resolve/add blockers
- Update "Next Priorities" to reflect what's next

**Idempotency check:** strip the "Last updated" line from old and new content, hash both. Matching hashes (unchanged substance): skip the write entirely, including the date — prevents "ran twice" from compounding drift via timestamp churn.

---

## Step 4: Write the session-log entry

Prepend to `session-log.md` (after the header, before existing entries):

```
## YYYY-MM-DD - [one-line title]

- [what changed - name files specifically]
- [decisions made or insights locked]
- [what's next / what was left open]

---
```

3-5 bullets. Past tense. Specific.

If the log now has more than 10 entries, archive the oldest — see [`references/log-rotation.md`](references/log-rotation.md).

---

## Step 5: Update hub files, manifest summaries, and `_CLOSETS.md`

Only update hubs for domains touched this session. Read the Hub Map for each hub; scan touched folders for `*-index.md` files too (catches hubs created informally, without `/memex:add-domain`).

**5a. Hub-table entries (legacy hubs only).** Touched hub with a prose `[domain]-index.md` file/table: update per [`references/legacy-hubs.md`](references/legacy-hubs.md). Closets-only hubs (v2.1+ default) skip this; new files land in `_CLOSETS.md` via 5c. Always update `_MANIFEST.md`'s one-line summaries when Tier 1/Tier 2 content changes meaningfully, per the 8 rules in [`references/summary-rules.md`](references/summary-rules.md) (benchmark-validated 90.1% R@5 — don't paraphrase).

**5b. Status sections in touched domain files.** Scan files read/edited this session for status-like sections (`## Status`, `## Current State`, `## Progress`); update any made stale (e.g. still "planned" when done, counts/dates that no longer hold). Touched files only.

**5c. Refresh `_CLOSETS.md` for touched hubs.** Refresh each touched hub's `_CLOSETS.md` (sibling of the hub index, e.g. `programs/_CLOSETS.md`) — the typed-field index future sessions scan. Format/semantics/pagination/fallback: [`references/closets-format.md`](references/closets-format.md) (read once per session). Quick rules: one `## [[stem]]` heading per file; `subjects`/`people`/`claims`/`decisions`/`dates`/`status` lines (omit empty); cap ~1500 chars/entry; only touched-this-session files; create if missing. Over 30 entries: paginate per the reference (includes Recently Archived).

**5d. Refresh `memory/_CLOSETS.md`.** Touched Tier 1 file (`status.md`, `session-log.md`, `decisions.md`, `glossary.md`, or user-added like `contacts.md`): refresh its entry — same format, no pagination. Missing on 2.1.x+: create from `memory-closets.md.tmpl`, seed every Tier 1 file.

**Self-check.** Re-read each summary written/updated this session — would it surface every named subject in the top 5 manifest hits? Missing subject: add it.

---

## Step 6: Scan for untracked content

Scan for files/folders not in any hub or the manifest (skim content). Flag folders with 3+ untracked markdown files (likely domains — note name, count, apparent topic from content) and loose untracked project files (note which domain fits, or if it's a new one). Build a list for the close-report; keep it fast — session-end *surfaces* this, dedup/contradiction sweeps are `/memex:consolidate`'s job.

---

## Step 7: Log decisions

Meaningful decisions this session: append to `decisions.md`:

```
**YYYY-MM-DD** - [decision stated as a fact, one sentence]
```

Append-only — session-end doesn't compress. At/above 95 lines after appending: nudge the close report (`decisions.md at <N> lines; run /memex:consolidate --fix to compress`); don't block close. No decisions: skip this step.

---

## Step 8: Verify wikilinks (broken + scoped suggest)

**8a. Wikilink integrity.** Run against the workspace (`--skip .claude .obsidian .git` + any scratch path):

```
python3 "${CLAUDE_SKILL_DIR}/scripts/verify-wikilinks.py" "$WORKSPACE_ROOT" --skip .claude .obsidian .git
```

Not found: report "Wikilink script not found - skipping" — don't silently pass. Broken links: fix them; target is zero.

**8b. Wikilink suggest (scoped to this session).** Files created/modified this session (Step 2's summary): run a scoped suggest pass for new plain-text refs that should be wikilinks:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/verify-wikilinks.py" "$WORKSPACE_ROOT" --suggest --files <file1> <file2> ... --skip .claude .obsidian .git
```

Hits: surface in the close report; auto-apply only unambiguous matches (exact case-fold match to an existing file), list ambiguous ones (short stems, multiple candidates) for the user to route. No files touched: skip 8b. Proportional version of `/memex:wikilinks --suggest` — run that for full sweeps.

**8c. Typed-edge graph (deferred).** No longer rebuilt at session-end — refreshes lazily via `/memex:reindex`/`/memex:consolidate` (both run `extract-graph.py`). Frontmatter-bearing file touched this session: mention it in the close report:

> `frontmatter touched this session — run /memex:consolidate or /memex:reindex to refresh memory/.graph.md`

Informational; don't block close.

**8d. Self-test.** Verify each prior step's output landed:

- `status.md` — "Last updated" today (or unchanged if Step 3 idempotent-skipped)
- `session-log.md` — new entry at top, today's date
- Hub files for touched domains (legacy hubs only) — every added/modified file listed
- `_CLOSETS.md`/`memory/_CLOSETS.md` — entry for every touched file
- `_MANIFEST.md` — summary-format-version marker still `:2`
- Wikilink check — exited 0 (CLEAN)

Any failure: surface in Step 9 as `[INCOMPLETE]` next to the step. Drift is louder than silence.

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

Append if triggered — untracked content (Step 6) or an ideas inbox with routes:

```
Untracked content:
  [folder]/ ([count] files about [topic]) - /memex:add-domain [name]
  [file.md] (fits in [domain]/) - say "organize files" to move it
```

```
Ideas inbox: [count] items
  "[title]" -> [domain]. Say "route ideas" to move ready items.
```

**Consolidate cadence nag.** Skip if workspace < 14 days old (`_MANIFEST.md` mtime) — nothing to sweep yet. Otherwise check `memory/.consolidate-runs.log`'s last line: missing or > 14 days old, append `Last /memex:consolidate: [N days ago | never]. Consider running it for a deeper drift sweep.`; else omit. One-line nudge — informational, doesn't block close.

---

## Step 10: Write session-close marker

`$CLAUDE_PLUGIN_DATA` set and exists: append to `$CLAUDE_PLUGIN_DATA/session-closes.log`:

```
YYYY-MM-DDTHH:MM:SS  workspace-root-basename  clean
```

Best-effort, never blocks close — no lock to clear; session-start/session-end are stateless.

---

## Wikilink rules during session-end

- Every file reference in a hub table uses `[[filename]]` format; every new hub file gets one.
- File renamed/moved this session: search `[[old-name]]` across all `.md` files, update to `[[new-name]]`.

---

## Gotchas

- **Session-end is the most common timeout victim** — partial updates may land; session-start's mtime check catches it (its Step 1), run `/memex:lint` if drift is suspected.
- **No session lock** (v2.1+ dropped `.session.lock`) — unconditional, idempotent (Step 3 hashes to skip no-op writes); bulk-write skills keep their own locks for real concurrency.
- **Typed-edge graph is rebuilt by reindex/consolidate, not here** — a frontmatter change just nudges the close report; one-session lag has no retrieval impact (additive/regenerable).
- **Idempotency is intentional** (Step 3) — a no-op status.md write is correct, not a bug.
- **The 30-entry closets cap is a hard budget** — route overflow to `_CLOSETS-archive.md` per [`references/closets-format.md`](references/closets-format.md).
- **Informally created hub files** are found by scanning `*-index.md` in *touched* folders only — untouched domains wait for a future session.
- **Decisions.md is append-only here** — compression lives in `/memex:consolidate`; the 100-line cap just nudges the close report.
- **Summary content is benchmark-validated, not style** — dropping verbatim facts ("allergic to coffee" → "has dietary restrictions") tanks R@5; follow [`references/summary-rules.md`](references/summary-rules.md) literally.
- **Closets archive is not loaded eagerly** — the fallback fires only on a primary-closets miss (deterministic grep, session-start Step 4); pagination sorts by underlying-file mtime.
