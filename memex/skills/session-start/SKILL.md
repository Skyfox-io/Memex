---
name: session-start
description: >
  Use when opening a Memex session: at the SessionStart hook, after `/clear`, when context
  feels stale mid-session, or when resuming after a break. Detects workspace state, scans
  the manifest, loads tiered context (status / session-log / decisions / ideas), pre-loads
  the relevant domain via `_CLOSETS.md`, and outputs a 30-second briefing.
---

# Memex - Session Start

**Wikilink rule:** when referencing files in any markdown you write, use `[[filename]]` format. Plain-text filenames break Obsidian graph connectivity.

Orient yourself and deliver a tight briefing so the session starts at full speed.

## Step 1: Detect workspace state and check session lock

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists at the workspace root:

- **No manifest:** tell the user "Memex is installed but not initialized in this workspace. Run `/memex:init` to set up structured memory here." Stop.
- **Manifest with `<!-- memex-managed:N.N.N -->` marker:** parse the version. If the major version is older than the current Memex VERSION (read `memex/.claude-plugin/plugin.json` if accessible — the v2 baseline is `2.0.0`), this is an outdated workspace. Continue normally, but in Step 6 append a one-line `Memex upgrade available — run /memex:upgrade to migrate to v2 retrieval.` notice. Otherwise, full Memex mode. Continue.
- **Manifest without marker but with Tier 1/2/3 structure:** compatible mode. Continue. After Step 6's briefing, append: "Running in compatible mode. Run `/memex:init` to enable full features, then `/memex:upgrade` to migrate to v2 retrieval."

### Crash-recovery check

Read `memory/.session.lock` if it exists.

- **Lock present, ≤ 24h old:** previous session may have crashed without running session-end. After the briefing, append: "⚠ Previous session may not have closed cleanly (lock at `memory/.session.lock` from [timestamp]). Status and session-log may be drifted — run `/memex:update` to refresh, or `/memex:lint` for a full health check before working."
- **Lock present, > 24h old:** stale lock from an earlier crash. Same warning, plus "lock is stale; clearing it."
- **Lock missing:** clean state, no warning.

Then write a fresh lock:

```
memory/.session.lock contains: 2026-05-04T15:42:18  pid=<pid>  agent=<agent>
```

Session-end clears it on clean close.

## Step 2: Scan the manifest

Read `_MANIFEST.md`. Use the one-line summaries in the Tier 1 and Tier 2 tables to understand what's in the workspace without opening every file. Learn the Hub Map to know which hub owns which domain.

Resolve file paths via this chain (first match wins):

1. Config table in `_MANIFEST.md` (if present)
2. Convention (`memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `memory/glossary.md`, `scratch/ideas.md` or `ideas.md`)
3. Search by name

## Step 3: Load context

Read these in order:

1. `status.md` — full file. Current priorities and blockers.
2. `session-log.md` — read from the top, stop after the first `---` separator. That's the most recent entry. Don't read older entries.
3. `decisions.md` — last 5 entries.
4. `ideas.md` — skim, note routing destinations.

If any file is missing, note briefly and continue. Do not stop.

After reading status.md, parse "Last updated" and calculate days between that and today. If more than 3 days, flag for the briefing.

## Step 4: Pre-load relevant domain

If the user's opening message mentions a specific domain, identify the right hub from the manifest summaries.

**Read the hub's `_CLOSETS.md` first** (e.g., `programs/_CLOSETS.md`) — sibling of the hub index. The closets file is a typed-field index that enumerates the distinct subjects, named entities, decisions, and status of every file in the hub, so you can decide which files to actually open without reading each.

For the full closets schema, field semantics, and pagination policy, see [`../session-end/references/closets-format.md`](../session-end/references/closets-format.md). Read it once if you haven't this session.

**Field-level retrieval is the point.** A "what about Mike" question looks at `people:`; a "when did I switch to Linear" question looks at `decisions:` and `dates:`; a "what did I tell you about my allergies" question looks at `claims:`. Treat each typed field as a separate searchable line, not a sub-bullet of the file's overall topic.

Wikilinks in a closets entry tell you a file exists; they do not mean you should open it. Open a file only when the current task requires its full content.

If no `_CLOSETS.md` exists for the hub (workspace pre-dates v2 or hub not yet curated), fall back to reading the hub index file directly. Note the gap — Step 6 surfaces it.

### Closets coverage scan

If the workspace has no `<!-- memex-managed` marker (compatible mode predates v2 closets), skip this scan — pre-v2 workspaces don't owe closets coverage.

Otherwise, after loading the active hub, scan every `[[*-index]]` row in the Hub Map and check whether `<hub-folder>/_CLOSETS.md` exists. Count hubs with coverage vs without. If any hub is missing closets, hold the count for the briefing.

### Closets archive fallback

`_CLOSETS.md` is capped at 30 entries (most recently modified). Larger hubs spill older entries into a sibling `_CLOSETS-archive.md`, which session-start does **not** load by default.

If you scan `_CLOSETS.md` and find no entry that matches the user's question — but the question still seems to live in this hub — load `<domain>/_CLOSETS-archive.md` (if it exists) and scan it before opening individual files. Same format, same field-level retrieval logic.

Do not load the archive eagerly; only on a primary-closets miss.

## Step 5: Scan for untracked content

Scan the workspace for markdown files and folders not listed in any hub or the manifest. For files in folders, read briefly to understand content. Look for:

- Folders with 3+ markdown files not in the Hub Map
- Loose files at the root or in untracked folders that look like project documents

Build a short list of suggestions for the briefing.

## Step 6: Output the briefing

No preamble. No pleasantries. Exact format:

---

**Status:** [one sentence from status.md Active Focus]

If status.md is more than 3 days stale, insert this line; otherwise skip:

**Stale:** Status is [N] days old (last updated [date]). Consider "Update first" below, or run `/memex:lint` for a full health check.

**Last session:** [2-3 bullets from the most recent session-log entry]

**In flight:**
- [items from status.md What's In Progress]

**Blocked:**
- [items from status.md What's Blocked]

**Relevant decisions:** [1-2 entries from decisions.md that directly constrain today's likely work. Omit if nothing applies.]

**Ideas inbox:** [each item with suggested routing destination. If empty: "Empty."]

---

If Step 5 found untracked content, append:

```
Untracked content detected:
  [folder]/ ([count] files, appears to be about [topic]) - /memex:add-domain [name]
  [file.md] (looks like it belongs in [domain]/) - move it? say "organize files"
```

If Step 1 detected an outdated `<!-- memex-managed:1.x.x -->` marker, append:

```
Memex upgrade available — workspace is on v1; run /memex:upgrade to migrate to v2 retrieval.
```

If Step 4's coverage scan found hubs without `_CLOSETS.md`, append:

```
Closets missing for [N] of [M] hubs — run /memex:reindex to backfill.
```

(One line, only if at least one hub is missing. If every hub is covered, omit.)

After the briefing (and any notices), end with two options:

```
→ **Start session** - jump straight in
→ **Update first** - flag what's changed since last session
```

If the user picks "update first" (or says anything indicating items have changed), ask what's different, then update `status.md` immediately before proceeding. If they pick "start session" (or just state their task), move on — don't ask again.

## Output rules

- Briefing should take 30 seconds to read. If longer than ~20 lines, trim it.
- Surface only what's actionable.
- Use `[[filename]]` wikilink format when referencing files.
- Wikilinks are pointers, not load triggers. Seeing `[[brand-voice]]` in a file doesn't mean you should load it. Only load files when the current task requires them.

---

## Gotchas

- **Sessions that time out or get abandoned don't run session-end**, so status.md and session-log.md may not reflect the last session's work. The staleness warning catches this. If the user sees a warning, suggest "Update first" before diving in.
- **Session-start reads only the most recent session-log entry** (stops at first `---`). If the file format is corrupted (missing separators), you'll read too much. The session-log format requires `---` after every entry — flag and ask if you encounter a malformed file.
- **The "Update first" option** lets users correct drift before working. If they pick it, update status.md immediately, then proceed.
- **Closets are pointers, not load triggers** — same rule as wikilinks. Listing 12 files in `_CLOSETS.md` doesn't mean you read 12 files. Read closets once, decide which 0–2 files the task actually needs, open only those.
- **Field-level retrieval beats topic-level retrieval.** When matching the user's question against a closets entry, scan typed fields (`people:`, `claims:`, `decisions:`, `dates:`) before assuming the headline subject covers it. The benchmark win comes from this; ignoring typed fields ignores the moat.
- **Lock written before failure means lock leaked.** If you write the lock in Step 1 then crash before Step 6 lands cleanly, the next session-start sees a fresh-looking lock. The crash-recovery check catches this only by age — your lock will look "active" until 24h passes. Acceptable trade-off; flagged here for diagnosis.
