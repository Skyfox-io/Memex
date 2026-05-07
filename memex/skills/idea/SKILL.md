---
name: idea
description: >
  Quick-capture an idea to the scratch inbox. Use only when the user explicitly asks to capture
  an idea: phrases like "capture this", "add to ideas", "don't let me forget", "log this idea",
  "/memex:idea ...", or any direct request to save a side thought without breaking flow. Do NOT
  fire on every "we should eventually..." or "what if" aside in conversation; most asides are
  not capture-intent. Not for routed work (lives in domain hubs), decisions (lives in decisions.md),
  or facts (lives in /memex:facts).
argument-hint: "[idea description]"
---

# Memex - Capture Idea

**Wikilink rule:** In any markdown you write, reference files as `[[filename]]`.

Quick-capture to the scratch inbox. Routing happens later (session-end or on demand).

## Step 1: Resolve the inbox path

Search order:
1. Workspace config table, if present.
2. `scratch/ideas.md`.
3. `ideas.md` at workspace root.

If none exist, create `scratch/ideas.md` (or `ideas.md` at root if there's no `scratch/` folder).

## Step 2: Capture

Take the idea text from `$ARGUMENTS` or the user's message. If genuinely ambiguous, ask one clarifying question. Otherwise just capture.

Append:

```markdown

### [brief title] - YYYY-MM-DD
[idea in 1-3 sentences]
-> Suggested route: [domain folder from Hub Map, or "unrouted"]
```

If `_MANIFEST.md` exists, read its Hub Map to suggest a route. Otherwise mark `unrouted`.

## Step 3: Confirm

```
Idea captured: "[brief title]"
  -> Suggested route: [domain path or "unrouted"]
  Saved to: [resolved path]
```

Don't route now. Routing is session-end's job, or runs when the user asks.

## Gotchas

- **Don't route eagerly.** If the route looks obvious, still write to the inbox. Batched routing at session-end avoids fragmenting the inbox and lets the user review.
- **Inbox file missing mid-session.** If the file vanished (renamed, moved), don't recreate silently in a new location. Re-resolve via the search order above; only create fresh when nothing matches.
- **Not for facts or decisions.** A claim about state ("Alice now leads X") goes through `/memex:facts`. A locked-in choice goes in `decisions.md`. The inbox is for *unprocessed* sparks.
- **One idea per entry.** If the user dumps three ideas at once, append three blocks, not one merged blob. Routing works per-entry.
