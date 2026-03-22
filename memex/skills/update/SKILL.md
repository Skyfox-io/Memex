---
name: update
description: >
  Mid-session sync - flush current status and decisions to memory without closing the session.
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

## Step 4: Confirm

```
Memory updated.

status.md - updated [date]
Decisions: [count logged, or "none"]

Session still open. Run /memex:session-end to close fully.
```
