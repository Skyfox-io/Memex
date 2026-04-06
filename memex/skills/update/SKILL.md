---
name: update
description: >
  Mid-session sync -- flush current status and decisions to memory without closing the session.
  Use when you want to checkpoint progress, after a significant decision, or before stepping away.
---

# Memex - Update

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Flush current session state to memory files. No session-log entry. No hub updates. No wikilink checks.

---

## Step 1: Resolve paths

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Resolve paths using: Config table (if present) > convention (`memory/`) > search.

If `_MANIFEST.md` does not exist, tell the user: "Memex is not initialized. Run `/memex:init` first." and stop.

---

## Step 2: Update status.md

- Update "Last updated" to today's date
- Update "What's In Progress" to reflect current state
- Update "What's Blocked" - resolve anything unblocked, add new blockers
- Update "Next Priorities" if they've shifted

---

## Step 3: Log decisions

If meaningful decisions have been made this session, append to decisions.md:

```
**YYYY-MM-DD** - [decision stated as a fact, one sentence]
```

Skip if no decisions were made.

---

## Step 4: Annotate superseded decisions

Scan decisions.md for entries where a later entry explicitly overrides an earlier one. Look for language in newer entries that references older decisions: "supersedes", "replaces", "dropped", "no longer", "instead of", "reverses".

For each match:
1. Find the older entry being referenced
2. If it's not already struck through, wrap it in ~~strikethrough~~
3. Append ` (superseded YYYY-MM-DD)` with the date of the newer entry

Only annotate when the override relationship is explicit in the text. Do not infer contradictions from similar topics -- that's what /memex:lint is for.

Skip this step if decisions.md has fewer than 5 entries.

---

## Step 5: Confirm

```
Memory updated.

status.md - updated [date]
Decisions: [count logged, or "none"] ([N] superseded entries annotated)

Session still open. Run /memex:session-end to close fully.
```

---

## Gotchas

- decisions.md should stay under 100 lines. If it's approaching that after logging, compress related entries from the same time period into summary entries.
- Only annotate decisions where the supersession is explicit in the text. Don't infer contradictions from topical similarity.
