---
name: session-start
description: >
  Session briefing - auto-invoke at every session open. Reads status, log, decisions, ideas, delivers briefing.
---

# Memex - Session Start

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames. This is critical for [Obsidian](https://obsidian.md/) graph connectivity.

Orient yourself and deliver a tight briefing so the session starts at full speed.

## Step 1: Detect workspace state

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists at the workspace root.

- **No manifest:** Tell the user "Memex is installed but not initialized in this workspace. Run `/memex:init` to set up structured memory here." Then stop.
- **Manifest with `<!-- memex-managed` marker:** Full Memex mode. Continue to Step 2.
- **Manifest without marker but with Tier 1/2/3 structure:** Compatible mode. Continue to Step 2. After the briefing, append: "Running in compatible mode. Run `/memex:init` to enable full features."

## Step 2: Scan the manifest

Read `_MANIFEST.md`. Use the one-line summaries in the Tier 1 and Tier 2 tables to understand what's in the workspace without opening every file. Learn the Hub Map to know which hub owns which domain.

Resolve file paths using this chain (first match wins):

1. **Config table** in `_MANIFEST.md` (if a Config section exists, use its values)
2. **Convention** (standard locations: `memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `memory/glossary.md`, `scratch/ideas.md` or `ideas.md`)
3. **Search** (find the file by name in the workspace)

## Step 3: Load context

Read these files in order:

1. `status.md` - current priorities and blockers. Read the full file.
2. `session-log.md` - read from the top and stop after the first `---` separator. This is the most recent entry. Do not read older entries.
3. `decisions.md` - last 5 entries
4. `ideas.md` - skim it, note routing destinations

If any file is missing, note it briefly and continue. Do not stop.

## Step 4: Pre-load relevant domain

If the user's opening message mentions a specific domain or topic, read that domain's hub file now. Use the manifest summaries to identify the right hub without opening all of them.

## Step 5: Scan for untracked content

Scan the workspace for markdown files and folders not listed in any hub or the manifest. For files in folders, read them briefly to understand their content. Look for:

- **Folders with 3+ markdown files** not in the Hub Map
- **Loose files at the root or in untracked folders** that appear to be project documents

Build a short list of suggestions for the briefing output.

## Step 6: Output the briefing

No preamble. No pleasantries. Exact format:

---

**Status:** [one sentence from status.md Active Focus]

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

After the briefing (and any notices), add one line: "What are we working on today?" Then stop.

## Notes

- Briefing should take 30 seconds to read. If longer than ~20 lines, trim it.
- Only surface what's actionable.
- Use `[[filename]]` wikilink format when referencing files.
- Wikilinks are pointers, not load triggers. Seeing `[[brand-voice]]` in a file doesn't mean you should load brand-voice.md. Only load files when the current task requires them.
