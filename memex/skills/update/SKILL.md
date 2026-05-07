---
name: update
description: >
  Mid-session checkpoint: flush current status and decisions to memory without writing a
  session-log entry, hub updates, or wikilink checks. Use only when the user explicitly asks
  to checkpoint — phrases like "update memory", "checkpoint progress", "save status",
  "/memex:update", or directly after a significant decision the user wants persisted before
  stepping away. Do NOT fire on every shift in conversation or whenever your own context
  feels heavy — that's not a checkpoint trigger. For a clean close, use `/memex:session-end`
  instead.
---

# Memex - Update

**Wikilink rule:** when referencing files in any markdown you write, use `[[filename]]` format.

Mid-session sync. Flushes status and decisions only. No session-log entry. No hub updates. No `_CLOSETS.md` refresh. No wikilink checks. For a full close, use `/memex:session-end`.

---

## Step 1: Resolve paths

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Resolve paths via: Config table (if present) > convention (`memory/`) > search.

If `_MANIFEST.md` does not exist, tell the user "Memex is not initialized. Run `/memex:init` first." and stop.

---

## Step 2: Update status.md

- Update "Last updated" to today
- Update "What's In Progress" to reflect current state
- Update "What's Blocked" — resolve unblocked items, add new blockers
- Update "Next Priorities" if they've shifted

---

## Step 3: Log decisions

If meaningful decisions have been made this session, append to `decisions.md`:

```
**YYYY-MM-DD** - [decision stated as a fact, one sentence]
```

Skip if no decisions were made.

---

## Step 4: Annotate superseded decisions

Scan `decisions.md` for entries where a later entry explicitly overrides an earlier one. Look for language in newer entries referencing older decisions: *supersedes*, *replaces*, *dropped*, *no longer*, *instead of*, *reverses*.

For each match:

1. Find the older entry being referenced.
2. If not already struck through, wrap it in `~~strikethrough~~`.
3. Append ` (superseded YYYY-MM-DD)` with the date of the newer entry.

Only annotate when the override is explicit in the text. Do not infer contradictions from topical similarity — that's `/memex:lint`'s job.

Skip this step if `decisions.md` has fewer than 5 entries.

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

- **Update is not session-end.** It deliberately skips session-log, hub summaries, `_CLOSETS.md`, wikilink check, typed-edge graph, and lock clearing. If the session is actually ending, use `/memex:session-end` — otherwise the next session-start will see a stale state and warn.
- **Decisions.md must stay under 100 lines.** When approaching the cap after logging, compress related entries from the same time period into summary entries. Don't truncate — that loses retrieval signal.
- **Supersession detection is text-explicit only** (Step 4). Do not infer from topical similarity. If two decisions about the same project don't reference each other, they're both live until `/memex:lint` flags the contradiction.
- **No idempotency check here** (unlike session-end Step 3). Running `/memex:update` twice in a row will refresh the "Last updated" date both times even if nothing else changed. That's fine for a checkpoint primitive — but means update is *not* a substitute for session-end's idempotent close.
