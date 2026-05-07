---
name: consolidate
description: >
  Sweep the workspace for drift -- duplicate files, contradicted facts, and orphans -- on a
  separate cadence from session-end. Use after a multi-agent push, before a milestone, daily
  on heavily-used workspaces, when /memex:lint flags long-standing drift, or when the user
  says "clean up", "consolidate", or "find duplicates". Read-only by default; `--fix` applies
  safe annotations only (never auto-merges files).
argument-hint: "[--fix] [--force]"
disable-model-invocation: true
---

# Memex - Consolidate

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Independent drift sweep that session-end deliberately doesn't do. Three phases run in order: dedup, contradictions, orphans. Read-only by default; `--fix` only applies safe annotations.

---

## Step 0: Detect workspace and acquire lock

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash. Confirm `_MANIFEST.md` exists; if not, tell the user to run `/memex:init` and stop.

Acquire `memory/.consolidate.lock` and check the 24-hour cooldown in `memory/.consolidate-runs.log`. Both follow the shared bulk-write convention — see [`references/locking.md`](references/locking.md).

---

## Step 1: Dedup

Detect candidate duplicate files:

1. List all `.md` files in domain folders. Skip `memory/`, `scratch/`, `.git`, `.obsidian`, `.claude`, `memex`.
2. Group files where:
   - Filename stems are similar (Levenshtein distance ≤ 2 on lowercase stems), OR
   - Top wikilinks (the 5 most frequent `[[targets]]` cited inside) overlap by ≥ 80%.
3. For each group of ≥ 2 candidates, list: file path, file size, last-modified date, one-line summary of subject overlap.

**Output but do not auto-merge.** Dedup is user-confirmed always — `--fix` does not auto-merge files.

---

## Step 2: Contradiction sweep

Resolve `facts.py` (`${CLAUDE_PLUGIN_ROOT}/scripts/facts.py` → `${CLAUDE_SKILL_DIR}/../../scripts/facts.py`). Run `facts.py contradictions`. It surfaces every `(subject, predicate)` pair with multiple distinct current objects.

For each contradiction:

- Show the pair, all conflicting fact IDs, and objects.
- Suggest: `Run /memex:facts supersede <id> '<correct value>'`.

**With `--fix`:** if a contradiction has only two facts and one is clearly older (by `valid_from`), supersede the older one automatically and log the change. Otherwise, leave for user resolution.

---

## Step 3: Orphan check

Three sub-checks.

### 3a. Wikilink dangling

Run `verify-wikilinks.py` (path resolution as in [session-end](../session-end/SKILL.md) Step 8a). Report broken wikilinks. With `--fix`, do nothing — broken wikilinks need user judgment.

### 3b. Frontmatter dangling

Run `extract-graph.py --check` (path resolution as in session-end Step 8b). Report typed edges pointing to missing files.

### 3c. Hub orphans

For each domain in the Hub Map: list `.md` files on disk that aren't in the hub's table (excluding the hub index itself, `_CLOSETS.md`, and `_CLOSETS-archive.md`). These are files dropped in the folder without being wired up.

With `--fix`, propose adding them to the hub. Don't auto-add — wikilink summaries need user/agent judgment.

---

## Step 4: Record the run

Append to `memory/.consolidate-runs.log` (format in [`references/locking.md`](references/locking.md)):

```
YYYY-MM-DDTHH:MM:SS  dedup=<N> contradictions=<M> orphans=<K>  status=<ok|partial>
```

Clear `memory/.consolidate.lock`.

---

## Step 5: Output report

```
Memex Consolidation Report

DEDUP: [PASS / N candidate groups]
  [...]

CONTRADICTIONS: [PASS / N pairs]
  (subject) (predicate): {old object → new object} -- run /memex:facts supersede <id> '<value>'
  [...]

ORPHANS: [PASS / N files]
  Wikilinks: [N broken / CLEAN]
  Typed-edge graph: [N dangling / CLEAN]
  Hub orphans: [path - "fits domain X" if known]
  [...]

Last run: [from .consolidate-runs.log]
```

End with: `Run /memex:lint for the per-check live report at any time.`

---

## Gotchas

- The lock is best-effort. A killed process leaves it stale. Stale locks (over 30 min old) are treated as freed — see [`references/locking.md`](references/locking.md).
- `--fix` only auto-supersedes contradictions where one fact is clearly older by `valid_from`. Anything ambiguous waits for the user.
- Dedup never auto-merges. `--fix` is for safe annotations only.
- Consolidate is the dedup/contradiction/orphan owner; session-end stays lean by deferring this work here. Run consolidate on its own cadence, not as a session-end appendage.
- For closets coverage gaps, run `/memex:reindex`. For summary format upgrades, run `/memex:resummarize`. Consolidate doesn't rebuild closets or summaries.
