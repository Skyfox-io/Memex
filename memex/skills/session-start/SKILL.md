---
name: session-start
description: >
  Use when opening a Memex session: at the SessionStart hook, after `/clear`, when
  resuming after a break, or when context feels stale mid-session. Loads tiered
  context and outputs a briefing.
---

# Memex - Session Start

**Wikilink rule:** When referencing files in any markdown you write, use `[[filename]]` format. Plain-text filenames break Obsidian graph connectivity.

Orient fast, deliver a tight briefing.

## Step 1: Detect workspace state

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check `_MANIFEST.md` at the workspace root:

- **No manifest:** tell the user to run `/memex:init` to set up structured memory here, then stop.
- **Marker present and current:** full Memex mode, continue.
- **Anything else** (no marker, or an outdated marker): read [`references/workspace-modes.md`](references/workspace-modes.md), then continue.

**Unclean-close detection (mtime-based).** No session lock exists. If any workspace `.md` file (excluding `.git`, `.claude`, `.obsidian`, `memex`, `node_modules`) is newer than `status.md` by 5+ minutes, the previous session likely skipped session-end — append after the briefing:

> ⚠ Files were modified after the last `status.md` update. The previous session may not have closed cleanly. Run `/memex:update` to refresh status, or describe what's been happening and we'll capture it.

Otherwise no warning — the only state check, no lock file involved.

## Step 2: Scan the manifest

Read `_MANIFEST.md`'s Tier 1/Tier 2 summaries and Hub Map (hub-to-domain mapping) without opening every file.

Resolve paths (first match wins): manifest config table → convention (`memory/status.md`, `session-log.md`, `decisions.md`, `glossary.md`, `scratch/ideas.md` or `ideas.md`) → search by name.

## Step 3: Load context

Read in order: `status.md` (full file — priorities/blockers) → `session-log.md` (top entry only, stop at first `---`) → `decisions.md` (last 5 entries) → `ideas.md` (skim, note routing) → `memory/_CLOSETS.md` if present (typed-field index over Tier 1 files — subjects/people/claims/decisions/dates/status — for field-level lookups instead of re-scanning full text).

Missing file: note briefly, continue. If `memory/_CLOSETS.md` is missing on a 2.1.x+ workspace, flag it for Step 6 (`memory closets missing — run /memex:reindex --hub memory`).

Parse `status.md`'s "Last updated" date; if more than 3 days old, flag for the briefing.

## Step 4: Pre-load relevant domain

If the opening message names a domain, find its hub from the manifest summaries and **read the hub's `_CLOSETS.md` first** (sibling of the hub index, e.g. `programs/_CLOSETS.md`) — a typed-field index over the hub's files, so you decide what to open without reading each. No `_CLOSETS.md`: fall back to the hub index, note the gap for Step 6. Schema/semantics/pagination: [`../session-end/references/closets-format.md`](../session-end/references/closets-format.md) (read once).

**Field-level retrieval is the point:** "what about Mike" → `people:`; "what did I tell you about X" → `claims:`. Each typed field is its own searchable line, not a sub-bullet of the file's topic.

**Graph hint.** If the message names an entity and `memory/.graph.md` exists, `grep -i "<entity>" memory/.graph.md` first — typed edges (`people`, `supersedes`, `blocks`) surface files closets alone may miss. Graph lags reindex/consolidate; treat hits as hints, not ground truth.

**Closets coverage scan.** Skip in compatible mode (no marker — pre-v2 workspaces don't owe coverage). Otherwise check every Hub Map hub for `<hub-folder>/_CLOSETS.md`; hold the covered-vs-missing count for Step 6.

**Closets archive fallback (deterministic).** On a primary-closets miss, grep 2-4 key terms from the question across every `_CLOSETS-archive.md` before opening files:

```bash
find "$WORKSPACE_ROOT" -name '_CLOSETS-archive.md' -exec grep -il -e "term1" -e "term2" {} +
```

Read any hit (same field-level logic). No hits: proceed as today. Never load archives eagerly.

## Step 5: Scan for untracked content

Scan for markdown files/folders not listed in any hub or manifest (skim to understand content). Flag folders with 3+ untracked files, and loose root/untracked files that look like project docs. Build a short suggestion list for the briefing.

## Step 6: Output the briefing

No preamble. No pleasantries. Exact format:

---

**Status:** [one sentence from status.md Active Focus]

**Stale:** [Only when status.md is >3 days old, else omit this line: Status is [N] days old (last updated [date]). Consider "Update first" below, or run `/memex:lint` for a full health check.]

**Last session:** [2-3 bullets from the most recent session-log entry]

**In flight:**
- [items from status.md What's In Progress]

**Blocked:**
- [items from status.md What's Blocked]

**Relevant decisions:** [1-2 entries from decisions.md that directly constrain today's likely work. Omit if nothing applies.]

**Ideas inbox:** [each item with suggested routing destination. If empty: "Empty."]

---

Append if triggered — untracked content (Step 5), outdated v1 marker (Step 1), or closets coverage gaps (Step 4; omit if every hub is covered):

```
Untracked content detected:
  [folder]/ ([count] files, appears to be about [topic]) - /memex:add-domain [name]
  [file.md] (looks like it belongs in [domain]/) - move it? say "organize files"
```

```
Memex upgrade available — workspace is on v1; run /memex:upgrade to migrate to v2 retrieval.
```

```
Closets missing for [N] of [M] hubs — run /memex:reindex to backfill.
```

Always end with:

```
→ **Start session** - jump straight in
→ **Update first** - flag what's changed since last session
```

"Update first" (or signs of drift): ask what changed, update `status.md`, then proceed. "Start session" (or stating the task): move on. Don't ask twice.

## Output rules

- Briefing takes 30 seconds to read; trim if longer than ~20 lines.
- Surface only what's actionable.
- Use `[[filename]]` wikilink format when referencing files.
- Wikilinks and closets entries are pointers, not load triggers — seeing `[[X]]` doesn't mean load it; only load files the current task requires.

---

## Gotchas

- **Timed-out sessions skip session-end** — the unclean-close check (Step 1) catches the resulting staleness; suggest "Update first" if seen.
- **Only the most recent session-log entry loads** (stops at first `---`). A malformed file (missing separators) reads too much — flag and ask if you hit one.
- **"Update first"** updates status.md immediately, then proceeds.
- **Closets and wikilinks are pointers, not load triggers.** See Output rules — read closets once, decide which 0–2 files the task needs, open only those.
- **Field-level retrieval beats topic-level** (Step 4) — this is the benchmark win; ignoring typed fields ignores the moat.
- **No session lock** (v2.1+ dropped it) — staleness detection uses mtimes instead (Step 1); the 5-minute window absorbs clock drift, not session-start's own writes.
- **Graph hints can lag.** `memory/.graph.md` refreshes only via `/memex:reindex` or `/memex:consolidate`, not every session. A miss doesn't mean no relationship exists; a hit should still be checked against current content.
