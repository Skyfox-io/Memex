---
name: cross-search
description: >
  Trigger when the user's question spans multiple Memex workspaces and
  they don't know which one holds the answer; e.g., "where did we land
  on the spring fundraising plan?" with separate nonprofit and personal
  workspaces, or "have I written about X anywhere?". Also use when the
  user explicitly asks to search across linked sources. Reads only
  manifests and closets, never inside individual files.
argument-hint: "<query>"
---

# Memex - Cross-Workspace Search

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Grep across every searchable workspace in `~/.memex/sources.md`, grouped by source. Reads only `_MANIFEST.md`, every `_CLOSETS.md`, and every `_CLOSETS-archive.md`. Fast and deterministic.

Registry conventions, script-path resolution, and privacy semantics: see `references/registry.md`. CLI surface: `memex/scripts/sources.py`.

## Step 1: Query

Use `$ARGUMENTS` as the query. If empty, ask: "What do you want to search for across linked workspaces?"

## Step 2: Confirm sources exist

`python3 <sources.py> list`. If none searchable, tell the user: "No linked workspaces yet. Run `/memex:link-workspace` from a workspace to register it."

## Step 3: Search

```
python3 <sources.py> search "<query>"
```

The script greps each searchable source's `_MANIFEST.md`, `_CLOSETS.md`, and `_CLOSETS-archive.md` for matches. Results are grouped by source.

## Step 4: Format output

If results found:

1. Show grouped raw results (file path, line, match).
2. Per source with hits, suggest: "To dive in, switch to that workspace (`cd` to its path) and start a session."
3. If a hub by the same name appears across multiple sources, call that out.

If no results:

```
No matches for "<query>" across <N> linked sources.

Either:
- The subject hasn't been wikilinked into any manifest or closets file.
  /memex:resummarize in the relevant workspace would surface it.
- The subject lives only inside files (not in manifests/closets). Open
  the workspace directly to search inside files.
```

## Gotchas

- **Index-only search.** Manifests and closets. Never inside content files. Closets are the index, content is the body. If a subject isn't wikilinked into a closet, it's invisible here. Closets format spec: `memex/skills/session-end/references/closets-format.md`.
- **`searchable: false` is total.** A source opted out is skipped silently. No partial visibility.
- **Case-insensitive substring.** Regex chars in the query are escaped automatically; you can't use regex.
- **Missing path = silent skip per source.** If a workspace was moved after linking, cross-search prints `(path missing: ...)` for that source and continues. Fix with unlink + re-link.
