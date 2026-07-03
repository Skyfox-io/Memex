---
name: search
description: >
  Cross-hub search within the current workspace. Greps `_MANIFEST.md`, every
  hub's `_CLOSETS.md` / `_CLOSETS-archive.md`, `memory/_CLOSETS.md`, and
  `memory/.graph.md` (typed-edge graph, if present). Results are grouped by
  folder so cross-domain queries (e.g., "everywhere I mentioned Airtable",
  "decisions touching the spring campaign") surface every hub that has a
  hit. A built-in similarity pass supplements grep with fuzzy/paraphrase
  matching. Use when the question spans hubs, when you don't know which
  hub owns the answer, or when grep across the index files is the right
  tool. For cross-workspace search, use
  `/memex:cross-search`. Reads only manifest, closets, and graph — never
  inside individual files.
argument-hint: "<query>"
disable-model-invocation: true
---

# Memex - Search

**Wikilink rule:** When referencing files in any markdown you write, use `[[filename]]` format.

Cross-hub search within the current workspace. Same retrieval surface as `/memex:cross-search`, scoped to one workspace.

## Step 1: Resolve workspace and query

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Use `$ARGUMENTS` as the query. If empty, ask: "What do you want to search for across hubs in this workspace?"

If `_MANIFEST.md` is missing, tell the user "Memex isn't initialized in this workspace. Run `/memex:init` first." and stop.

## Step 2: Search

Run `${CLAUDE_SKILL_DIR}/scripts/sources.py`:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" search-local "<query>" --workspace "$WORKSPACE_ROOT"
```

The script greps `_MANIFEST.md`, every `_CLOSETS.md` and `_CLOSETS-archive.md`, and `memory/.graph.md` under the workspace. Output is grouped by folder.

## Step 2b: Similarity supplement (built-in)

Always run this after grep, never instead of it:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/semantic.py" query "<query>" --workspace "$WORKSPACE_ROOT"
```

Show hits under a `Similarity matches` section placed AFTER the grep results. Dedupe against grep hits: skip any result whose stem grep already surfaced.

## Step 3: Format output

If results found:

1. Show the script's grouped output verbatim (folder header, file:line:match lines).
2. Summarize what cuts across hubs: if the same query hits multiple hub folders, call that out — that's the cross-hub signal the user came for.
3. If a hit is in the Recently Archived section of a `_CLOSETS.md`, suggest loading the corresponding `_CLOSETS-archive.md` for full typed-field context on that file.

If no results (grep and Step 2b's similarity pass both found nothing):

```
No matches for "<query>" in this workspace.

Either:
- The subject isn't wikilinked into the manifest or any closets file.
  Run /memex:resummarize or /memex:reindex to refresh closets.
- The subject lives only inside content files. Open the relevant hub's
  files directly (closets surface what's *in* the index, not raw content).
- The similarity pass (Step 2b) also found nothing — the subject likely
  isn't indexed; run /memex:reindex.
```

## Step 4: Suggested follow-ups

After results, append a one-line nudge based on what was found:

- Hits in multiple hubs → "Cross-hub query confirmed: subject lives in `<hub-a>` and `<hub-b>`."
- Hits only in `_CLOSETS-archive.md` → "Recent activity is archived. Load the archive for full context."
- Hits in `memory/_CLOSETS.md` only → "Subject lives in Tier 1 (status / decisions / glossary / contacts)."

---

## Gotchas

- **Index-only search.** Manifest and closets. Never inside content files. If a subject isn't wikilinked into a closet, `/memex:search` won't see it. The fix is `/memex:resummarize` or `/memex:reindex`, not deeper grep.
- **Case-insensitive substring, grep-only.** Regex chars are escaped automatically; you can't use regex. The built-in similarity pass (Step 2b) is stdlib-only and catches morphological variants (fundraiser/fundraising) grep can't — but not true synonyms. Synonym-level matching engages automatically only in environments where `sentence-transformers` is already present (e.g. a local dev machine); nothing to install, nothing to configure.
- **Search is read-only.** No writes, no closets refresh. To fix gaps surfaced by a search, run `/memex:reindex` to refresh closets.
- **Cross-workspace lives elsewhere.** This skill scopes to one workspace. For "have I written about X in any of my workspaces", use `/memex:cross-search`.
- **Folder grouping uses path prefixes.** Hits in `programs/` group together; hits in `programs/subhub/` are a separate group. That's intentional — sub-hubs surface as independently as top-level hubs.
- **Semantic cache is derived and disposable, embedding mode only.** `memory/.semantic-cache/` only exists when `sentence-transformers` is present and the embedding engine ran — lexical mode writes nothing. Safe to delete any time; it rebuilds on the next `semantic.py query`. If the workspace is a git repo, consider adding it to `.gitignore`.
- **`.graph.md` hits are typed edges, not text matches.** A hit in `memory/.graph.md` means a frontmatter field (`people`, `supersedes`, `blocks`, etc.) named the query term. Follow the edge to the named file(s) rather than treating the hit itself as the answer.
