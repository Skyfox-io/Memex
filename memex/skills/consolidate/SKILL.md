---
name: consolidate
description: >
  Sweep the workspace for drift -- duplicate files, unannotated decision supersessions,
  orphans, and bloated decisions logs -- on a separate cadence from session-end. Use after
  a multi-agent push, before a milestone, daily on heavily-used workspaces, when
  /memex:lint flags long-standing drift, or when the user says "clean up", "consolidate",
  or "find duplicates". Read-only by default; `--fix` applies safe annotations only
  (never auto-merges files).
argument-hint: "[--fix] [--force]"
disable-model-invocation: true
---

# Memex - Consolidate

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Independent drift sweep that session-end deliberately doesn't do. Four phases run in order: dedup, decisions contradictions, orphans, decisions compression. Read-only by default; `--fix` only applies safe annotations.

---

## Step 0: Detect workspace and acquire lock

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash. Confirm `_MANIFEST.md` exists; if not, tell the user to run `/memex:init` and stop.

Acquire `memory/.consolidate.lock` and check the 24-hour cooldown in `memory/.consolidate-runs.log`. Both follow the shared bulk-write convention. See [`references/locking.md`](references/locking.md).

---

## Step 1: Dedup

Detect candidate duplicate files:

1. List all `.md` files in domain folders. Skip `memory/`, `scratch/`, `.git`, `.obsidian`, `.claude`, `memex`.
2. Group files where:
   - Filename stems are similar (Levenshtein distance ≤ 2 on lowercase stems), OR
   - Top wikilinks (the 5 most frequent `[[targets]]` cited inside) overlap by ≥ 80%.
3. For each group of ≥ 2 candidates, list: file path, file size, last-modified date, one-line summary of subject overlap.

**Output but do not auto-merge.** Dedup is user-confirmed always. `--fix` does not auto-merge files.

---

## Step 2: Decisions contradiction sweep

Read `decisions.md`. Scan newer entries for explicit override language referencing earlier entries:

> supersedes, replaces, dropped, no longer, instead of, reverses, overrides

For each match:

1. Find the older entry being referenced (string-match on the topic).
2. Check whether it's already annotated with `~~strikethrough~~` and `(superseded YYYY-MM-DD)`.

If unannotated:

- Show the pair: old entry text, new entry text.
- Suggest: "Annotate the old entry with strikethrough and a `(superseded <date>)` marker."

**With `--fix`:** Apply the strikethrough + supersession marker automatically. Same logic as `/memex:lint --fix`'s decision-consistency annotation.

This is keyword-explicit detection only. Don't infer contradictions from topical similarity. False positives are louder than false negatives in a write-back operation.

---

## Step 3: Orphan check

Three sub-checks.

### 3a. Wikilink dangling

Run `verify-wikilinks.py` (path resolution as in [session-end](../session-end/SKILL.md) Step 8a). Report broken wikilinks. With `--fix`, do nothing. Broken wikilinks need user judgment.

### 3b. Frontmatter dangling and graph refresh

Resolve `extract-graph.py` (`${CLAUDE_PLUGIN_ROOT}/scripts/extract-graph.py` → `${CLAUDE_SKILL_DIR}/../../scripts/extract-graph.py`).

First run with `--check` to surface dangling edges (typed references to missing files). Report each.

Then run without `--check` to rewrite `memory/.graph.md` with the current graph state. Consolidate is the regular refresh point for the graph (along with `/memex:reindex`); session-end no longer does this.

Skip both if the script is unresolvable. Typed edges are opt-in.

### 3c. Hub orphans

For each domain in the Hub Map: list `.md` files on disk that aren't in the hub's table (excluding the hub index itself, `_CLOSETS.md`, and `_CLOSETS-archive.md`). These are files dropped in the folder without being wired up.

With `--fix`, propose adding them to the hub. Don't auto-add. Wikilink summaries need user/agent judgment.

---

## Step 4: Decisions compression

Read `decisions.md`. If it has fewer than 60 lines, skip this phase entirely (no pressure on the 100-line cap).

Otherwise, scan the file for compression candidates by these concrete rules:

### 4a. Drop redundant supersession pairs

For each `~~strikethrough~~` entry annotated `(superseded YYYY-MM-DD)`, check whether the superseding entry exists later in the file and stands on its own. If yes, the strikethrough entry is now redundant detail.

**With `--fix`:** Replace the original verbose strikethrough entry plus its superseder with a single one-line summary:
```
**YYYY-MM-DD** - <new fact>; replaces <old fact> (was <YYYY-MM-DD>)
```
Without `--fix`: list the candidate pairs and the proposed merged form.

### 4b. Collapse same-period clusters

Group consecutive entries by ISO week (Monday-Sunday). For each week with ≥3 entries about overlapping topics (≥50% subject overlap based on noun matches in the entry text), the cluster is a candidate.

**With `--fix`:** Combine into one entry with sub-bullets, preserving every unique fact:
```
**YYYY-MM-DD–YYYY-MM-DD** - [topic]
  - <fact 1 verbatim>
  - <fact 2 verbatim>
  - <fact 3 verbatim>
```
Without `--fix`: list candidate clusters and proposed combined form.

### 4c. Compression bounds

Compression preserves every unique fact. If two entries say the same thing differently, keep the clearer one verbatim. If they say different things, keep both as sub-bullets. Never paraphrase. Never drop a fact because it "feels redundant" — the test is "would re-reading this in 6 months recover the same retrieval signal?"

If `decisions.md` is at or above 95 lines and `--fix` is not set, surface a hard warning in the report: "decisions.md at <N> lines; approaching 100-line cap. Run /memex:consolidate --fix to compress."

---

## Step 5: Record the run

Append to `memory/.consolidate-runs.log` (format in [`references/locking.md`](references/locking.md)):

```
YYYY-MM-DDTHH:MM:SS  dedup=<N> decisions-contradictions=<M> orphans=<K> decisions-compressed=<D>  status=<ok|partial>
```

Clear `memory/.consolidate.lock`.

---

## Step 6: Output report

```
Memex Consolidation Report

DEDUP: [PASS / N candidate groups]
  [...]

DECISIONS CONTRADICTIONS: [PASS / N unannotated pairs]
  Old: <text> -- New: <text> -- fix: add ~~strikethrough~~ + (superseded YYYY-MM-DD)
  [...]

ORPHANS: [PASS / N files]
  Wikilinks: [N broken / CLEAN]
  Typed-edge graph: [N dangling / CLEAN]
  Hub orphans: [path - "fits domain X" if known]
  [...]

DECISIONS COMPRESSION: [PASS / N candidates / N applied]
  decisions.md: [N] lines
  Supersession pairs: [count]
  Same-period clusters: [count]
  [...]

Last run: [from .consolidate-runs.log]
```

End with: `Run /memex:lint for the per-check live report at any time.`

---

## Gotchas

- The lock is best-effort. A killed process leaves it stale. Stale locks (over 30 min old) are treated as freed. See [`references/locking.md`](references/locking.md).
- `--fix` only annotates explicit decision supersessions (newer entry literally references the older with "supersedes/replaces/dropped/no longer/instead of/reverses/overrides"). Anything ambiguous waits for the user.
- Dedup never auto-merges. `--fix` is for safe annotations only.
- **Decisions compression preserves every unique fact.** Never paraphrase; never drop a fact because it feels redundant. The test is whether re-reading the compressed log in 6 months still recovers the original retrieval signal. Verbatim user-stated facts ("allergic to coffee", "raised $42K") stay verbatim.
- **Decisions compression is the only place this happens.** Session-end no longer compresses decisions — it only appends. This skill is the compression owner; run it when `decisions.md` approaches the 100-line cap.
- Consolidate is the dedup/contradiction/orphan/decisions-compression owner; session-end stays lean by deferring this work here. Run consolidate on its own cadence, not as a session-end appendage.
- For closets coverage gaps, run `/memex:reindex`. For summary format upgrades, run `/memex:resummarize`. Consolidate doesn't rebuild closets or summaries.
