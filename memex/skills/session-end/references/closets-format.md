# `_CLOSETS.md` Format

Canonical schema for the per-hub typed-field index. This file is the single source of truth. Other skills (session-start, add-domain, reindex, resummarize) should link here rather than duplicate.

For the summary writing rules that govern the *content* of each field, see [[summary-rules]].

---

## Schema

```markdown
# Closets: <hub-name>

<!-- memex-closets:1.0 -->

## [[file-stem-1]]
- subjects: <comma-separated distinct topics, including mid-file mentions and acronyms>
- people: [[Alice]], [[Bob]]
- claims: <verbatim user-stated facts: "allergic to coffee", "I'm a teacher", "3 kids">
- decisions: <recent decisions, switches, rejections, abandons logged in or affecting the file>
- dates: <month names, years, relative dates, absolute dates mentioned in the file>
- status: active | superseded | archived

## [[file-stem-2]]
...
```

## Field semantics

Each typed field is independently retrievable. Future Claude sessions retrieve by field-level attention:

- `subjects:`. Breadth of distinct topics. Pull from anywhere in the file (mid-paragraph, list items, ALL-CAPS acronyms), not just headings.
- `people:`. Named people, as `[[wikilinks]]`. Answers "what about Mike?".
- `claims:`. User-stated facts, **verbatim**. Answers "what did I tell you about my allergies?".
- `decisions:`. Switches, rejections, abandons, picked-X-over-Y. Answers "why did I leave Asana?".
- `dates:`. Month names, years, relative ("last March"), absolute ("3/15"). Answers temporal-reasoning questions.
- `status:`. `active`, `superseded`, or `archived`.

Treat each field as its own searchable line, not a sub-bullet of the file's overall topic.

## Cross-section invariants

- One `## [[stem]]` heading per file in the hub.
- The `<!-- memex-closets:N.M -->` marker stays on the second line.
- Cap each file entry at ~1500 chars.
- Omit lines for fields the file doesn't have; don't write empty bullets.
- Only refresh entries for files actually touched this session. Other entries stay untouched.
- If `_CLOSETS.md` doesn't exist for a touched hub, create it.

## Pagination policy (30-entry cap)

`_CLOSETS.md` is capped at **30 entries** so session-start can load it cheaply. Overflow moves to a sibling `_CLOSETS-archive.md` that is **not** loaded eagerly.

After refreshing this session's entries, if `_CLOSETS.md` would contain more than 30:

1. Sort all entries (existing + this session's) by **modification time of the underlying file** (most recently modified first).
2. The top 30 stay in `_CLOSETS.md`.
3. The remainder move to `_CLOSETS-archive.md`. Prepend above existing archive content; never overwrite.
4. Bump the version marker to `<!-- memex-closets:1.1 -->` in both files.
5. If `_CLOSETS-archive.md` is created for the first time, add `[[<hub>-CLOSETS-archive]]` to the Tier 3 table of `_MANIFEST.md`.
6. Append a **Recently Archived** section to the primary `_CLOSETS.md` listing the top 5 most recently demoted file stems, one line each:
   ```
   ## Recently Archived
   - [[stem-1]] — <subjects fragment>, last touched YYYY-MM-DD
   - [[stem-2]] — <subjects fragment>, last touched YYYY-MM-DD
   ...
   ```
   This surfaces the archive's existence and most recently demoted contents in the always-loaded layer. Field-level retrieval still uses the 30 primary entries. The Recently Archived list is informational; it tells session-start "the archive isn't empty, here's what it contains" without expanding the retrieval surface.

When an archived file is touched again, its entry promotes back to `_CLOSETS.md` and the oldest primary entry (by underlying file mtime) demotes to the archive. Recently Archived list is regenerated on each pagination.

The archive has no hard cap. Past ~100 entries, run `/memex:consolidate` for dedup candidates.

## The `memory/` hub

`memory/_CLOSETS.md` indexes Tier 1 files (status, session-log, decisions, glossary, plus any user-added Tier 1 entries). It does **not** paginate (Tier 1 is a small fixed set). No archive, no Recently Archived section.

Tier 1 files always auto-load at session-start, but their closets entries enable typed-field retrieval against them — "what did the user say about Mike?" hits `people:` and `claims:` instead of scanning every line of every Tier 1 file.

## Read-side fallback

Session-start does **not** load `_CLOSETS-archive.md` by default. If a primary-closets scan misses but the question still seems to live in this hub, load the archive and scan it before opening individual files. Same format, same field-level retrieval logic.

## Why this format

The manifest's one-line summaries surface a *hub* to a question. The closets entries surface the *specific file inside the hub*. Without closets, recall on questions like "what did I tell you about Mike?" requires opening every file in the hub.

The typed-field structure is validated in `benchmarks/longmemeval/`: on the LongMemEval-S 500-question retrieval benchmark, the closets representation hits **90.1% R@5**, within 0.5pp of `content:bm25` (the upper bound that indexes the entire raw session text) at roughly 1/10th the size. The argument is size-vs-recall, not raw-recall-against-keyword-search; full caveats and the retrieval-vs-QA distinction live in the benchmarks README. The structural win is field-level attention: a question zooms to one typed field instead of competing against unrelated subjects in the same blob.
