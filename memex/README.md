# Memex

Structured memory for Claude. Persistent context across sessions, so Claude starts every conversation already oriented — not from scratch.

**90.1% Recall@5 on [LongMemEval-S](https://huggingface.co/datasets/xiaowu0162/longmemeval)** (Wu et al., ICLR 2025). Reproducible in 3-5 minutes, $0. See `benchmarks/longmemeval/`.

## What it does

- **Tiered context loading** — Tier 1 always-load files, Tier 2 domain hubs on demand, Tier 3 archived. Claude only reads what it needs.
- **Two-tier index** — `_MANIFEST.md` plus per-hub `_CLOSETS.md` files mean Claude knows what every file contains *without opening any of them*. Field-typed retrieval (subjects / people / claims / decisions / dates / status) — the moat behind the 90.1% R@5 result.
- **Temporal facts** — SQLite sidecar (`memory/.facts.db`, stdlib only) tracks `(subject, predicate, object)` triples with `valid_from`/`valid_to` dates. Mike got promoted? The old fact gets stamped, not overwritten. Contradiction detection catches drift.
- **Typed-edge graph** — optional YAML frontmatter (`supersedes`, `blocks`, `people`, `projects`) auto-extracted into a knowledge graph at session-end. Pure regex; zero LLM calls.
- **Cross-workspace federation** — register multiple workspaces in a global registry; search across all of them with `/memex:cross-search`. Privacy-first: opt-in per source.
- **Wikilinks everywhere** — every file reference becomes `[[wikilink]]` format. Open in Obsidian to see the graph.
- **Zero dependencies** — markdown plus Python stdlib. No database server, no API keys, no embeddings backend, no cloud.

## Quick start

1. Open a Cowork session in your workspace.
2. Type `/memex:init`.
3. Done — future sessions auto-brief via the SessionStart hook.

Empty workspace? Init scaffolds in under 30 seconds. Existing files? Init scans and wires them into a manifest without moving anything.

**Upgrading from v1?** Open a session in any v1 Memex workspace; the briefing will surface a `Memex upgrade available — run /memex:upgrade` prompt. One command, idempotent on re-run.

## Skills

| Skill | What it does |
|-------|-------------|
| `/memex:init` | Set up, adopt, or health-check a workspace |
| `/memex:upgrade` | One-command v1→v2 migration: orchestrates resummarize + reindex + lint, idempotent on re-run |
| `/memex:session-start` | Briefing at session open |
| `/memex:session-end` | Close cleanly: update memory, log decisions, refresh closets, verify links + graph |
| `/memex:update` | Mid-session flush: save status without closing |
| `/memex:idea` | Quick-capture an idea to the inbox |
| `/memex:add-domain` | Add a new domain folder with hub index and closets file |
| `/memex:archive` | Move a file from active to archived in the manifest |
| `/memex:wikilinks` | Check for broken links and convert plain text references to `[[wikilinks]]` |
| `/memex:lint` | Audit workspace health: stale status, contradictions, orphans, dangling typed edges, summary version, missing closets |
| `/memex:resummarize` | Refresh manifest + hub summaries to v2 retrieval-tuned format |
| `/memex:reindex` | Backfill or rebuild every hub's `_CLOSETS.md` |
| `/memex:facts` | Query, add, or reconcile temporal facts in the SQLite knowledge graph |
| `/memex:consolidate` | Run dedup, contradiction sweep, and orphan check (independent of session-end) |
| `/memex:link-workspace` | Register the current workspace in the global source registry |
| `/memex:unlink-workspace` | Deregister a workspace from the global source registry |
| `/memex:cross-search` | Grep across linked workspaces' manifests + closets, plus query each source's facts.db |

## How it works

`_MANIFEST.md` at the workspace root is a routing map — it tells Claude what files exist, which tier they belong to, and what each domain hub is. Per-hub `_CLOSETS.md` files extend that with typed-field summaries of every file's distinct subjects, named entities, decisions, and dates — so Claude can decide which 0–2 files a question actually needs without opening 12.

The `memory/` folder holds always-loaded files: `status.md`, `session-log.md`, `decisions.md`, `glossary.md`. Kept small so loading them doesn't burn context.

Domain folders hold actual work. Claude only reads domain files when a task requires them.

Convention over configuration: files in standard locations are found automatically. No config required unless your workspace uses non-standard paths.

## Requirements

- Cowork (Claude desktop app) or Claude Code
- A workspace folder

## License

MIT
