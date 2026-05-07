---
name: session-start
description: >
  Use when opening a Memex session: at the SessionStart hook, after `/clear`, when context
  feels stale mid-session, or when resuming after a break. Detects workspace state, scans
  the manifest, loads tiered context (status / session-log / decisions / ideas), pre-loads
  the relevant domain via `_CLOSETS.md`, and outputs a 30-second briefing.
---

# Memex - Session Start

**Wikilink rule:** When referencing files in any markdown you write, use `[[filename]]` format. Plain-text filenames break Obsidian graph connectivity.

Orient yourself and deliver a tight briefing so the session starts at full speed.

## Step 1: Detect workspace state

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists at the workspace root:

- **No manifest:** Tell the user "Memex is installed but not initialized in this workspace. Run `/memex:init` to set up structured memory here." Stop.
- **Manifest with `<!-- memex-managed:N.N.N -->` marker:** Parse the version. If the major version is older than the current Memex VERSION (read `memex/.claude-plugin/plugin.json` if accessible. The v2 baseline is `2.0.0`), this is an outdated workspace. Continue normally, but in Step 6 append a one-line `Memex upgrade available. Run /memex:upgrade to migrate to v2 retrieval.` notice. Otherwise, full Memex mode. Continue.
- **Manifest without marker but with Tier 1/2/3 structure:** Compatible mode. Continue. After Step 6's briefing, append: "Running in compatible mode. Run `/memex:init` to enable full features, then `/memex:upgrade` to migrate to v2 retrieval."

### Unclean-close detection (mtime-based)

There is no session lock. Instead, compare `status.md`'s mtime against the most recent `.md` file mtime anywhere in the workspace (excluding `.git`, `.claude`, `.obsidian`, `memex`, `node_modules`).

If any workspace `.md` file's mtime is more recent than `status.md`'s mtime by more than 5 minutes, the previous session likely modified files without running session-end. After the briefing, append:

> ⚠ Files were modified after the last `status.md` update. The previous session may not have closed cleanly. Run `/memex:update` to refresh status, or describe what's been happening and we'll capture it.

If `status.md` is the most recent (or within 5 minutes of the most recent), the workspace is clean. No warning.

This is the only state check. There is no lock file to clear, no "stale lock" semantics, no concurrent-session protection at the session level.

## Step 2: Scan the manifest

Read `_MANIFEST.md`. Use the one-line summaries in the Tier 1 and Tier 2 tables to understand what's in the workspace without opening every file. Learn the Hub Map to know which hub owns which domain.

Resolve file paths via this chain (first match wins):

1. Config table in `_MANIFEST.md` (if present)
2. Convention (`memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `memory/glossary.md`, `scratch/ideas.md` or `ideas.md`)
3. Search by name

## Step 3: Load context

Read these in order:

1. `status.md`. Full file. Current priorities and blockers.
2. `session-log.md`. Read from the top, stop after the first `---` separator. That's the most recent entry. Don't read older entries.
3. `decisions.md`. Last 5 entries.
4. `ideas.md`. Skim, note routing destinations.
5. `memory/_CLOSETS.md` if it exists. Typed-field index over Tier 1 files. Use for field-level lookups against status / session-log / decisions / glossary / contacts without re-scanning their full text. Same field semantics as hub closets (subjects / people / claims / decisions / dates / status).

If any file is missing, note briefly and continue. Do not stop. If `memory/_CLOSETS.md` is missing on a 2.1.x+ workspace, surface the gap in Step 6 ("memory closets missing — run `/memex:reindex --hub memory`").

After reading status.md, parse "Last updated" and calculate days between that and today. If more than 3 days, flag for the briefing.

## Step 4: Pre-load relevant domain

If the user's opening message mentions a specific domain, identify the right hub from the manifest summaries.

**Read the hub's `_CLOSETS.md` first** (e.g., `programs/_CLOSETS.md`). Sibling of the hub index. The closets file is a typed-field index that enumerates the distinct subjects, named entities, decisions, and status of every file in the hub, so you can decide which files to actually open without reading each.

For the full closets schema, field semantics, and pagination policy, see [`../session-end/references/closets-format.md`](../session-end/references/closets-format.md). Read it once if you haven't this session.

**Field-level retrieval is the point.** A "what about Mike" question looks at `people:`; a "when did I switch to Linear" question looks at `decisions:` and `dates:`; a "what did I tell you about my allergies" question looks at `claims:`. Treat each typed field as a separate searchable line, not a sub-bullet of the file's overall topic.

Wikilinks in a closets entry tell you a file exists; they do not mean you should open it. Open a file only when the current task requires its full content.

If no `_CLOSETS.md` exists for the hub (workspace pre-dates v2 or hub not yet curated), fall back to reading the hub index file directly. Note the gap. Step 6 surfaces it.

### Closets coverage scan

If the workspace has no `<!-- memex-managed` marker (compatible mode predates v2 closets), skip this scan. Pre-v2 workspaces don't owe closets coverage.

Otherwise, after loading the active hub, scan every `[[*-index]]` row in the Hub Map and check whether `<hub-folder>/_CLOSETS.md` exists. Count hubs with coverage vs without. If any hub is missing closets, hold the count for the briefing.

### Closets archive fallback

`_CLOSETS.md` is capped at 30 entries (most recently modified). Larger hubs spill older entries into a sibling `_CLOSETS-archive.md`, which session-start does **not** load by default.

If you scan `_CLOSETS.md` and find no entry that matches the user's question. But the question still seems to live in this hub. Load `<domain>/_CLOSETS-archive.md` (if it exists) and scan it before opening individual files. Same format, same field-level retrieval logic.

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

If the user picks "update first" (or says anything indicating items have changed), ask what's different, then update `status.md` immediately before proceeding. If they pick "start session" (or just state their task), move on. Don't ask again.

## Output rules

- Briefing should take 30 seconds to read. If longer than ~20 lines, trim it.
- Surface only what's actionable.
- Use `[[filename]]` wikilink format when referencing files.
- Wikilinks are pointers, not load triggers. Seeing `[[brand-voice]]` in a file doesn't mean you should load it. Only load files when the current task requires them.

---

## Gotchas

- **Sessions that time out or get abandoned don't run session-end**, so status.md and session-log.md may not reflect the last session's work. The mtime-based unclean-close check catches this. If the user sees the warning, suggest "Update first" before diving in.
- **Session-start reads only the most recent session-log entry** (stops at first `---`). If the file format is corrupted (missing separators), you'll read too much. The session-log format requires `---` after every entry. Flag and ask if you encounter a malformed file.
- **The "Update first" option** lets users correct drift before working. If they pick it, update status.md immediately, then proceed.
- **Closets are pointers, not load triggers.** Same rule as wikilinks. Listing 12 files in `_CLOSETS.md` doesn't mean you read 12 files. Read closets once, decide which 0–2 files the task actually needs, open only those.
- **Field-level retrieval beats topic-level retrieval.** When matching the user's question against a closets entry, scan typed fields (`people:`, `claims:`, `decisions:`, `dates:`) before assuming the headline subject covers it. The benchmark win comes from this; ignoring typed fields ignores the moat.
- **No session lock.** v2.1+ dropped `memory/.session.lock`. Unclean-close detection uses file mtimes instead. The 5-minute window absorbs minor clock drift; tighter windows produce false positives from manifest writes during session-start itself.
