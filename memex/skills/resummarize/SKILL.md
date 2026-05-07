---
name: resummarize
description: >
  Refresh manifest and hub summaries to v2 retrieval-tuned format. Use when
  upgrading from v1 (where summaries described topics) to v2 (where summaries
  enumerate distinct subjects, name entities, and quote user-stated facts
  verbatim), or after large content changes where existing summaries no longer
  reflect what's in the files.
argument-hint: "[--force]"
disable-model-invocation: true
---

# Memex - Resummarize

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Refresh manifest and hub summaries to current retrieval-tuned format. The companion to `/memex:reindex`:

- **Resummarize** — rewrites *summaries* (manifest Hub Map rows, Tier 1 file rows, per-file rows inside each hub).
- **Reindex** — rebuilds the per-hub `_CLOSETS.md` typed-field index.

Run resummarize first on a v1→v2 migration, then reindex. They're independent passes.

---

## Step 0: Detect workspace, acquire lock, detect format version

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash. Read `_MANIFEST.md`:

- **No `<!-- memex-managed` marker:** tell the user to run `/memex:init` first and stop.

Acquire `memory/.resummarize.lock` and check the 24-hour cooldown in `memory/.resummarize-runs.log`. Both follow the shared bulk-write convention — see `../consolidate/references/locking.md`.

Look for `<!-- summary-format-version:N -->` in the manifest:

- Marker says `2` and `--force` not passed: ask "Manifest is already v2-format. Resummarize anyway? (y/n)". If no, exit and clear the lock.
- Marker says `1` or absent: proceed.

---

## Step 1: Identify files to resummarize

Three layers, processed in this order (highest leverage first):

1. **Tier 1 files** in the manifest: `[[CLAUDE]]`, `[[status]]`, `[[session-log]]`, `[[decisions]]`, `[[glossary]]`, `[[ideas]]`, plus any other Tier 1 entries.
2. **Hub Map rows** in the manifest: every `[[*-index]]` one-line domain summary.
3. **Hub interiors**: every wikilinked entry inside each Tier 2 hub file.

---

## Step 2: Read each file and write a v2 summary

For each file, read its current content and rewrite the summary using the **eight v2 summary rules**: `../session-end/references/summary-rules.md`.

Highlights of the v2 contract (full rules in the reference):

- Enumerate distinct subjects from anywhere in the file, not just opening lines.
- Quote user-stated facts verbatim. Don't paraphrase.
- Name entities by name.
- Cap at 250 characters.
- Capture decision reversals and date/time mentions explicitly.

**Example transformation:**

v1 (loses retrieval on specific subjects):
> Tracks fundraising activities for spring campaign

v2 (surfaces for "Mike", "the gala", "donor list"):
> Spring fundraising; gala on 2026-04-15 at Pier 2; Mike is event lead; raised $42K so far; donor list at `[[donors-2026]]`; rejected sponsor SunCorp

---

## Step 3: Update the manifest version marker

Set in the manifest header:

```
<!-- summary-format-version:2 -->
```

If absent, add as the second comment line, immediately under `<!-- memex-managed:... -->`.

---

## Step 4: Verify, record the run, and report

Run `verify-wikilinks.py` (path resolution as in [session-end](../session-end/SKILL.md) Step 8) to confirm no links broke during the rewrite.

Append to `memory/.resummarize-runs.log`:

```
YYYY-MM-DDTHH:MM:SS  tier1=<N> hubmap=<M> hubinteriors=<K>  status=<ok|partial>
```

Clear `memory/.resummarize.lock`. Output:

```
Memex Resummarize Report

Tier 1: <N> files
Hub Map rows: <M>
Hub interiors: <K> entries across <H> hubs

Format version: now v2
Wikilinks: [PASS / N broken]

Summaries now enumerate distinct subjects and quote user-stated facts verbatim.
Run /memex:lint for a full health check, or /memex:reindex to rebuild closets.
```

---

## Gotchas

- **Don't fabricate subjects.** If a file doesn't mention a person by name, don't pad the summary with one. Verbatim means verbatim.
- **Respect the 250-char cap.** On long files, pick the most retrieval-relevant subjects. Recent and named entities beat generic claims.
- **Resummarize doesn't touch closets.** Run `/memex:reindex` afterward if hub `_CLOSETS.md` files also need to migrate to v2 typed-field format.
- **Side effect: stale status pruning.** If a touched `status.md` has items clearly completed (no longer in `decisions.md` or recent session-log), prune them while you're there. But this is a side effect, not the main job.
- **`ideas.md` rule:** the summary lists topics of pending ideas, not "user has ideas about productivity."
- For granular drift detection (orphans, contradictions, dangling links), use `/memex:lint` or `/memex:consolidate`.
