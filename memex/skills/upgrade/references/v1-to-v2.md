# v1 → v2 upgrade playbook

The signals `/memex:upgrade` checks when migrating a v1 workspace, what each signal means for the upgrade plan, and what changes the user should expect.

## State signals

| Signal | v1 value | v2 value (current) | Action if mismatch |
|---|---|---|---|
| `<!-- memex-managed:N.N.N -->` | `1.0.x` or `1.1.x` | `2.0.0` | Bump after other steps complete |
| `<!-- summary-format-version:N -->` | absent or `1` | `2` | Run `/memex:resummarize` |
| `<hub>/_CLOSETS.md` | absent | present, one per hub | Run `/memex:reindex` |
| `<!-- memex-closets:N.N -->` | n/a (file didn't exist) | `1.0` (≤30 files) or `1.1` (paginated) | Implicit on reindex |
| `memory/.facts.db` | absent | optional, populated on first `/memex:facts` use | None — facts are opt-in |
| `memory/.graph.md` | absent | optional, populated on session-end if any frontmatter exists | None — graph is opt-in |

## What gets rewritten vs created

`/memex:resummarize` **rewrites** existing content:

- Tier 1 manifest summaries (status, session-log, decisions, glossary, ideas)
- Tier 2 manifest summaries (each domain hub's one-line description)
- Per-file summaries inside each domain hub's table

It enumerates every distinct subject from each file's content, names entities, and quotes user-stated facts verbatim. The 8-rule format produces ~30% denser summaries than v1; some lines may be 2x as long.

`/memex:reindex` **creates** new files:

- `<hub>/_CLOSETS.md` for every hub in the Hub Map
- If a hub has > 30 files, also `<hub>/_CLOSETS-archive.md`, and a Tier 3 entry for the archive

Reindex never edits hub indexes or domain content files. Orphans (files in a domain folder but not in the hub table) get a closets entry and are flagged for user action.

## What stays untouched

- All Tier 2 / Tier 3 content files (your actual work)
- Hub index file *contents* (the file table. Except where resummarize rewrites the per-file summary column)
- `memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `memory/glossary.md`, `scratch/ideas.md` (their summaries are rewritten in the manifest, but the files themselves are not touched)
- All `[[wikilinks]]` (verified via `verify-wikilinks.py` after the upgrade; broken links surface but are not auto-fixed)

## Expected size deltas

For a typical 5-domain, 30-file workspace:

| Artifact | v1 | v2 |
|---|---|---|
| `_MANIFEST.md` | ~80 lines | ~110 lines (denser per-row summaries) |
| Per-hub index files | unchanged content, denser per-file summary column | same |
| `_CLOSETS.md` per hub (new) | — | ~10-30 entries × ~600 chars avg |
| `memory/.graph.md` (new, if frontmatter present) | — | ~one line per typed edge |

Net new disk: ~5-15 KB per hub. None of it is auto-loaded above what session-start already reads (manifest + tier 1); closets load only when a domain question fires.

## Things that can go wrong

1. **Resummarize hits a file with sparse content.** V2 summaries enumerate distinct subjects; if a file is mostly boilerplate or reference data, the summary may end up shorter than v1's. That's correct behavior. There are no subjects to enumerate. Don't pad.

2. **Reindex flags lots of orphans.** If users have been dropping files in domain folders without running `/memex:add-domain`, the upgrade surfaces them all at once. This is good. Orphans were invisible in v1. But the report can be long. Resolve incrementally; the upgrade itself is complete regardless.

3. **The 8 rules' "decision reversal" pattern (rule 7) can surprise.** A hub with a long history of pivots (switched from X to Y, abandoned Z, picked A over B) will get summaries that read more like a changelog than a topic descriptor. That's by design. Temporal questions ("why did we leave X?") need that explicit verb in the summary to surface.

4. **Closets pagination engages on the first reindex if a hub has > 30 files.** Pagination is a v2 feature; v1 workspaces never hit it. The upgrade applies the new layout in one pass.

5. **Manifest version marker bump is last.** If reindex fails partway, the workspace shows a v1 marker, an inconsistent mix of v1 and v2 summaries, and partial closets coverage. A subsequent `/memex:upgrade` re-detects this and resumes.

## Cost

Free. All operations are local: regex extraction, string rewriting, mtime checks, file writes. No LLM calls, no API costs, no external services.

## After the upgrade

Run a fresh `/memex:session-start` to verify:

- The briefing should look the same as before (status, in-flight, blocked, decisions).
- Pre-loading a domain should now read the hub's `_CLOSETS.md` first instead of opening files speculatively.
- `/memex:lint` should report PASS on the new checks (typed-edge graph integrity, summary-format-version compliance).

If anything looks off, `/memex:upgrade --force` re-runs every step on a clean pass. No state to recover from, just rewrites.
