---
name: facts
description: >
  Explicit-invocation only — the user (or another skill that explicitly chains to it) must
  type `/memex:facts <subcommand>`. Autonomous DB writes from model inference are a footgun:
  misinterpreting "Alice probably works at X" as a fact would silently create a false
  (subject, predicate, object) row. Subcommand surface: `query`, `add`, `timeline`,
  `contradictions`, `supersede`, `export`, `rebuild`, `ingest`, `stats`. For autonomous
  cross-workspace fact lookups, use `/memex:cross-search` — it queries every linked
  workspace's facts.db read-only without requiring this skill.
argument-hint: "[query | add | timeline | contradictions | supersede | export | rebuild | ingest | stats] ..."
disable-model-invocation: true
---

# Memex - Facts

**Wikilink rule:** when referencing files in markdown, use `[[filename]]`.

Thin wrapper around `memex/scripts/facts.py`. Full CLI in [`references/cli.md`](references/cli.md).

## Storage model

Two artifacts, one source of truth:

- **`memory/.facts.db`** — SQLite sidecar. Fast queries. May be `.gitignore`d.
- **`memory/facts.md`** — human-readable mirror. Committed. Rendered by `export`.

**Invariant:** the mirror is durable; the DB is regenerable. `rebuild` wipes the DB and reads the mirror back in. If the two drift, the mirror wins. After every mutation (`add`, `supersede`, `ingest`), run `export` to keep them in sync.

Each row is a `(subject, predicate, object)` triple with `valid_from` (set) and `valid_to` (`NULL` = current). Supersession closes the old row and inserts a new one with the same subject+predicate.

## Resolving the script

1. `${CLAUDE_PLUGIN_ROOT}/scripts/facts.py` (when set)
2. `${CLAUDE_SKILL_DIR}/../../scripts/facts.py` (fallback)

Always pass `--workspace $(pwd)`. If `memory/.facts.db` doesn't exist, run `init` first.

## High-leverage workflows

### Query a subject's current state
```
facts.py query Alice                  # all current facts
facts.py query Alice works_at         # one predicate
facts.py timeline Alice works_at      # full history with supersession arrows
```

### Record a new fact
```
facts.py add Alice works_at Anthropic --date 2024-01-15 --source-file memory/decisions.md
facts.py export
```

Pass `--date` for historical facts; otherwise `valid_from` is today.

### Supersede an outdated fact
When a fact changes (Alice moved teams, project renamed):
```
facts.py query Alice works_at         # find the ID of the stale row
facts.py supersede 42 "OpenAI"        # closes #42, inserts new row
facts.py export
```

### Resolve contradictions
`/memex:lint` and `facts.py contradictions` both surface subjects with multiple current objects for the same predicate. Pick the right one and `supersede` the others — newest entry usually wins, but check `timeline` first.

### Export to markdown / rebuild from markdown
- `export` — DB → `memory/facts.md`. Run after any mutation.
- `rebuild` — wipe DB, reload from `memory/facts.md`. Use after manual mirror edits or DB corruption.

## After mutating the DB

Every `add` / `supersede` / `ingest` must be followed by `export`. Otherwise the mirror drifts and the next `rebuild` will silently undo the change.

## Gotchas

- **Mirror-vs-DB drift.** Forgetting `export` after mutation leaves `memory/facts.md` stale. The next `rebuild` reads the mirror — your unexported edits vanish. Always export.
- **Manual mirror edits need rebuild.** Editing `memory/facts.md` by hand does not propagate to the DB. Run `rebuild` after.
- **Contradiction detection requires distinct objects.** Two identical `(subject, predicate, object)` rows are duplicates, not contradictions, and won't surface in `contradictions`. Use `stats` or `query` to spot dupes.
- **`valid_from` defaults to today.** Pass `--date YYYY-MM-DD` when adding historical facts, or the timeline misorders.
- **Auto-ingest is heuristic.** `ingest` only matches `**YYYY-MM-DD** — text` lines in `decisions.md`, and only extracts `Capitalized Subject + verb + object` patterns. Complex sentences are dropped silently; nuanced or multi-clause facts must be `add`ed explicitly. False positives happen — review `stats` after a large ingest.
- **DB locked.** SQLite holds a brief write lock; concurrent `add`/`export` from two shells can fail. Retry, or serialize via session-end.
- **Subject capitalization is preserved verbatim.** `Alice` and `alice` are different subjects. Pick a canonical form per entity and stick to it.

## Cross-skill notes

- `/memex:consolidate` calls `facts.py contradictions` (read-only); with `--fix` it can auto-supersede the clearly-older fact in two-fact pairs. Run `add` and `supersede` here, not from inside consolidate.
- `/memex:lint` does not read facts directly — surface contradictions via `/memex:consolidate`. Resolve via this skill, not by editing the mirror.
- `/memex:cross-search` queries `memory/.facts.db` across every linked workspace read-only — for "have I written about X anywhere", prefer cross-search over manually invoking facts in each workspace.
- Facts are workspace-scoped; they don't bleed across linked workspaces.
- **Explicit invocation only.** The skill is gated with `disable-model-invocation: true` so autonomous model triggers can't write to the DB. Every subcommand requires the user (or another skill) to type `/memex:facts <subcommand>`.
