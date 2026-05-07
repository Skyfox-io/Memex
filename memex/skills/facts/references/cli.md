# `facts.py` CLI reference

Authoritative reference for the temporal facts script. The skill covers high-leverage workflows; this file documents every subcommand and flag for unusual cases.

For full schema + ingest heuristics, see the docstring at the top of `memex/scripts/facts.py`.

---

## Invocation

```
python3 memex/scripts/facts.py [--workspace PATH] <subcommand> [args]
```

`--workspace` defaults to `cwd`. Resolve the script via `${CLAUDE_PLUGIN_ROOT}/scripts/facts.py`, falling back to `${CLAUDE_SKILL_DIR}/../../scripts/facts.py`.

## Subcommands

| Command | Args | Effect |
|---|---|---|
| `init` | — | Create empty `memory/.facts.db`. Idempotent. |
| `add` | `SUBJ PRED OBJ [--date YYYY-MM-DD] [--source-file PATH] [--source-line N] [--confidence FLOAT]` | Insert one fact. `--date` sets `valid_from` (default: today). |
| `query` | `SUBJ [PRED]` | List currently-valid facts (where `valid_to IS NULL`), newest first. |
| `timeline` | `SUBJ [PRED]` | All facts for subject, oldest first. `✓` = current, `✗` = superseded. |
| `contradictions` | — | Subjects with multiple distinct current objects for the same predicate. |
| `supersede` | `ID NEW_OBJ` | Close fact `ID` (set `valid_to=today`, `superseded_by=new_id`); insert new row with same subject+predicate. |
| `stats` | — | Total / current / superseded counts; top 10 predicates. |
| `export` | — | Render `memory/.facts.db` → `memory/facts.md`. Run after every mutation. |
| `rebuild` | — | Wipe `.facts.db` and reinsert from `memory/facts.md`. Mirror is the durable source. |
| `ingest` | — | Parse `memory/decisions.md` for `**YYYY-MM-DD** — claim` lines and extract subject-verb-object triples via `SIMPLE_FACT_RE`. Idempotent (dedups on subject+predicate+object+source). |

## Standard predicates

Conventions, not enforced. Lowercase, underscore-separated:

`is`, `has`, `prefers`, `named`, `located_at`, `started`, `ended`, `decided`, `supersedes`, `blocks`, `blocked_by`, `works_at`, `attends`, `owns`, `allergic_to`.

## Auto-ingest regex

`ingest` only fires on lines matching `**YYYY-MM-DD.** Text` inside `decisions.md`. The fact-extraction regex is `Capitalized Subject (1-3 words) + verb + object`. Anything more complex is silently dropped. For high-stakes facts, prefer `add`.
