---
name: session-end
description: >
  Close session - update memory files, log decisions, verify wikilink integrity
---

# Memex - Session End

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames. This is critical for Obsidian graph connectivity.

Leave the workspace in a clean, fully updated state so the next session starts with perfect context.

Work through each step in order. Do not skip steps. Do not ask for permission between steps - execute everything and report at the end.

---

## Step 1: Detect workspace and resolve paths

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check if `_MANIFEST.md` exists. If not, skip silently and stop.

If it exists (with or without `<!-- memex-managed` marker), resolve file paths using this chain:

1. **Config table** in `_MANIFEST.md` (if present)
2. **Convention** (`memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `scratch/ideas.md` or `ideas.md`)
3. **Search** (find by name)

---

## Step 2: Synthesize the session

Before touching any files, write a brief internal summary:
- What files were created, modified, or moved?
- Which domains were touched?
- What decisions were made?
- What was completed vs. left open?

---

## Step 3: Update status.md

- Update "Last updated" date to today
- Remove completed items from "What's In Progress"
- Update "What's Blocked" - resolve unblocked items, add new blockers
- Update "Next Priorities" to reflect what actually comes next

Keep this as a clean snapshot of right now.

---

## Step 4: Write the session-log entry

Add a new entry at the very top of session-log.md (after the header, before existing entries):

```
## YYYY-MM-DD - [one-line title]

- [what changed - name files specifically]
- [decisions made or insights locked]
- [what's next / what was left open]

---
```

3-5 bullets. Past tense. Specific.

If the log has more than 10 entries, archive the oldest:
1. Read session-log-archive.md in full. If it does not exist, create it with header `# Session Log - Archive`.
2. Prepend oldest entries above existing archive content. Never overwrite existing entries.
3. Check if `[[session-log-archive]]` is listed in the Tier 3 table of `_MANIFEST.md`. If not, add it now:
   ```
   | [[session-log-archive]] | Older session log entries | YYYY-MM-DD |
   ```

---

## Step 5: Update hub files

Only update hubs for domains actually touched this session.

Read the Hub Map to identify which hub owns each domain. Also scan for any `*-index.md` file in folders where files were touched this session - this catches domains created informally.

For each relevant hub: add new files with `[[filename]]` wikilinks, a one-line summary of the file's content, and status. Update the status of existing entries. Every file in a hub table must have a `[[wikilink]]`.

Also update the one-line summaries in `_MANIFEST.md` if the content of any Tier 1 or Tier 2 file changed meaningfully this session. The manifest summaries should reflect current content so future session-starts can scan without opening files.

---

## Step 6: Scan for untracked content

Scan the workspace for files and folders not listed in any hub or the manifest. For each, briefly read the content to understand what it's about.

**Folders with 3+ markdown files not in the Hub Map:** These are likely domains. Note the folder name, file count, and what the files appear to be about (based on content, not just filenames).

**Loose project files not in any hub:** Files at the workspace root or in untracked folders that look like project documents. Note which existing domain they'd fit in, or if they suggest a new domain.

Build a list for the confirm block.

---

## Step 7: Log decisions

If this session produced meaningful decisions, append them to decisions.md:

```
**YYYY-MM-DD** - [decision stated as a fact, one sentence]
```

If decisions.md is approaching 100 lines, compress related entries. Keep it under 100 lines. Skip this step if no decisions were made.

---

## Step 8: Verify wikilinks

Run the wikilink verification script. Resolve the script path:

1. `${CLAUDE_PLUGIN_ROOT}/scripts/verify-wikilinks.py` (if set)
2. `${CLAUDE_SKILL_DIR}/../../scripts/verify-wikilinks.py` (fallback)

Pass `--skip .claude .obsidian .git` plus any scratch directory path.

If the script can't be found, report: "Wikilink script not found - skipping." Do not silently pass.

If broken links are found, fix them. Target is always zero.

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

This is informational. The session is closed. Do not block on a response.

---

## Wikilink Rules

When creating or editing any markdown file during session-end:
- Every file reference in a hub table must use `[[filename]]` format
- Every new file added to a hub gets a `[[wikilink]]`
- If a file was renamed or moved this session, search for `[[old-name]]` in all `.md` files and update to `[[new-name]]`
