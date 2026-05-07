---
name: reindex
description: >
  Backfill or rebuild every hub's `_CLOSETS.md` from scratch. Use after upgrading
  a v1 workspace to v2 (so closets exist on session 1 instead of accumulating
  across many session-ends), after a large bulk import, or any time first-pass
  v2 retrieval quality is needed immediately.
argument-hint: "[--force] [--hub <hub-name>]"
disable-model-invocation: true
---

# Memex - Reindex

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Walk every Tier 2 hub in `_MANIFEST.md` and (re)generate `_CLOSETS.md` for each. Session-end refreshes touched hubs incrementally; reindex covers the long tail in one pass.

**Picking the right migration tool:**

- `/memex:resummarize` — rewrites manifest + hub *summaries* to v2 format.
- `/memex:reindex` — rebuilds the per-hub closets index used for retrieval.

Run resummarize for summary format upgrades, reindex for closets coverage. They're independent; on a fresh v1→v2 migration, run resummarize first, then reindex.

---

## Step 0: Detect workspace, acquire lock, parse arguments

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash. Read `_MANIFEST.md`:

- **Missing or no `<!-- memex-managed` marker:** tell the user "Memex isn't initialized here. Run `/memex:init` first." and stop.

Acquire `memory/.reindex.lock` and check the 24-hour cooldown in `memory/.reindex-runs.log`. Both follow the shared bulk-write convention — see `../consolidate/references/locking.md`.

Parse `$ARGUMENTS`:

- `--hub <name>` — limit to one hub (e.g., `--hub fundraising`). Useful for spot rebuilds.
- `--force` — rebuild every entry from scratch, ignoring mtime checks. Also bypasses the 24-hour cooldown.

---

## Step 1: Build the hub list

Read `_MANIFEST.md`, extract every `[[*-index]]` row from the Hub Map. Resolve absolute paths for each hub file and its parent folder. Closets file: `<hub-folder>/_CLOSETS.md`. Archive (if any): `<hub-folder>/_CLOSETS-archive.md`.

If `--hub <name>` was passed, filter to that hub.

---

## Step 2: For each hub, enumerate files

Read the hub index. List every `[[wikilink]]` from the file table — these are the canonical members. Also scan the hub's folder for `.md` files not in the table (orphans). Reindex includes orphans by default and flags them in the report.

For each file:

1. Skip if missing on disk (`/memex:lint` reports dangling hub-table entries separately).
2. Get its mtime via `stat`.
3. Skip if `_CLOSETS.md` has a current entry (closets file's mtime more recent than the underlying file's) and `--force` was not passed.
4. Otherwise, queue for rebuild.

---

## Step 3: Generate closets entries

For each queued file, read content and write a typed-field closets entry. The format and the eight retrieval-tuned summary rules that drive each field live with session-end:

- Closets format: `../session-end/references/closets-format.md`
- Summary rules: `../session-end/references/summary-rules.md`

Reindex applies them verbatim — do not deviate.

---

## Step 4: Apply pagination

For each hub, after generating entries:

1. Sort all entries (rebuilt + skipped-as-current) by underlying file mtime, most recent first.
2. Top 30 stay in `_CLOSETS.md`.
3. Remainder go to `_CLOSETS-archive.md`, **prepended** above existing archive content (never overwrite older archive entries).
4. Both files use marker `<!-- memex-closets:1.1 -->`.
5. If `_CLOSETS-archive.md` is created for the first time, add `[[<hub>-CLOSETS-archive]]` to the Tier 3 table of `_MANIFEST.md`.

If a hub has ≤ 30 files, write only `_CLOSETS.md` with marker `<!-- memex-closets:1.0 -->`.

---

## Step 5: Verify

Run `verify-wikilinks.py` (path resolution as in [session-end](../session-end/SKILL.md) Step 8) to confirm no closets entry references a missing file. List broken entries in the report; don't auto-delete.

---

## Step 6: Record the run and report

Append to `memory/.reindex-runs.log`:

```
YYYY-MM-DDTHH:MM:SS  hubs=<N> files=<K> refreshed=<R> skipped=<S>  status=<ok|partial>
```

Clear `memory/.reindex.lock`. Output:

```
Memex Reindex Report

Hubs processed: <N>
  <hub-name>: <K> files indexed (<refreshed> refreshed, <skipped> already current)
    <P> primary entries, <A> archived (if pagination triggered)
  ...

Orphans found (in folder but not in hub table):
  <hub-name>/<file.md> -- consider adding to [[<hub>-index]]
  ...

Closets issues: [PASS / N dangling references]
  ...

Total time: <Ts>
```

Append a one-line entry to `memory/session-log.md` if Memex is in full mode (skip in compatible mode):

```
## YYYY-MM-DD - /memex:reindex

- Reindexed <N> hubs, <K> files. <refreshed> refreshed, <skipped> already current.
- <orphans> orphans surfaced; <issues> closet issues to resolve.

---
```

---

## Gotchas

- **Reindex reads every hub-listed file.** Cheap on 50 files, several minutes on 500+. Use `--hub <name>` to scope when iterating.
- **Reindex never edits hub indexes.** Only writes `_CLOSETS.md` and `_CLOSETS-archive.md`. Orphans surface for user action, not auto-add.
- **`--force` rebuilds every entry from scratch.** Use after a closets format change, or if existing entries look wrong. Otherwise the mtime check is enough.
- **Manual closets edits reset mtime.** A user fixing a typo in `_CLOSETS.md` may cause some entries to skip on the next reindex. Pass `--force` if that matters.
- For granular drift detection (orphans, dangling links, contradictions), use `/memex:lint`. Reindex is the bulk-write counterpart to lint's read-only audit.
- For summary format upgrades, use `/memex:resummarize` — it operates on manifest and hub summaries, not on closets.
