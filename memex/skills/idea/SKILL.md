---
name: idea
description: >
  Capture an idea to the scratch inbox. Use when a new idea comes up during work.
argument-hint: "[idea description]"
---

# Memex - Capture Idea

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Quick-capture an idea to the scratch inbox without breaking the current flow.

## Step 1: Resolve ideas path

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Resolve the ideas file path: Config table (if present) > convention (`scratch/ideas.md` or `ideas.md`) > search for `ideas.md`.

If no ideas file exists anywhere, create it at `scratch/ideas.md` (or `ideas.md` at workspace root if no scratch folder exists).

## Step 2: Capture the idea

Take the idea from `$ARGUMENTS` or the user's message. If the message is vague, ask one clarifying question.

## Step 3: Append to ideas inbox

Append to the resolved path:

```markdown

### [brief title] - YYYY-MM-DD
[The idea in 1-3 sentences]
-> Suggested route: [domain folder from Hub Map, or "unrouted" if no manifest]
```

If `_MANIFEST.md` exists, read the Hub Map to suggest a routing destination.

## Step 4: Confirm

```
Idea captured: "[brief title]"
  -> Suggested route: [domain path or "unrouted"]
  Saved to: [resolved path]
```

Do not route the idea now. Routing happens at session-end or when the user asks.
