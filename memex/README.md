# Memex

Structured memory for Claude. Persistent context across sessions, so Claude starts every conversation already oriented, not from scratch.

Closets-format index in pure markdown matches full-content BM25 on retrieval recall (LongMemEval-S, R@5) at roughly 1/10th the size, with zero external dependencies. Reproduce in 3-5 minutes, $0. See `benchmarks/longmemeval/`. Retrieval recall is not end-to-end QA accuracy — see the benchmarks README for what's measured and what isn't.

## What it does

- **Tiered context loading.** Tier 1 always-load files, Tier 2 domain hubs on demand, Tier 3 archived. Claude only reads what it needs.
- **Two-tier index.** `_MANIFEST.md` plus per-hub `_CLOSETS.md` files (and `memory/_CLOSETS.md` for Tier 1) mean Claude knows what every file contains *without opening any of them*. Field-typed retrieval — subjects / people / claims / decisions / dates / status.
- **Typed-edge graph.** Optional YAML frontmatter (`supersedes`, `blocks`, `people`, `projects`) auto-extracted into a knowledge graph. Pure regex; zero LLM calls.
- **Cross-workspace federation.** Register multiple workspaces in a global registry; search across all of them with `/memex:cross-search`. Privacy-first: opt-in per source.
- **Within-workspace cross-hub search.** `/memex:search` greps the manifest + every closets file, grouped by folder.
- **Wikilinks everywhere.** Every file reference becomes `[[wikilink]]` format. Open in Obsidian to see the graph.
- **Zero dependencies.** Markdown plus Python stdlib. No database server, no API keys, no embeddings backend, no cloud.

## Quick start

1. Open a Cowork session in your workspace.
2. Type `/memex:init`.
3. Done. Future sessions auto-brief via the SessionStart hook.

Empty workspace? Init scaffolds in under 30 seconds. Existing files? Init scans and wires them into a manifest without moving anything.

**Upgrading from v1 or v2.0?** Open a session in any older Memex workspace; the briefing will surface a `Memex upgrade available. Run /memex:upgrade` prompt. One command, idempotent on re-run.

## Skills

| Skill | What it does |
|-------|-------------|
| `/memex:init` | Set up, adopt, or health-check a workspace |
| `/memex:upgrade` | One-command migration orchestrator (v1→v2, v2.0→v2.1, future versions) |
| `/memex:session-start` | Briefing at session open |
| `/memex:session-end` | Close cleanly: update memory, log decisions, refresh closets, verify links |
| `/memex:update` | Mid-session flush: save status without closing |
| `/memex:idea` | Quick-capture an idea to the inbox |
| `/memex:add-domain` | Add a new domain folder with closets (hub index optional) |
| `/memex:archive` | Move a file from active to archived in the manifest |
| `/memex:wikilinks` | Check for broken links and convert plain text references to `[[wikilinks]]` |
| `/memex:lint` | Audit workspace health: stale status, supersession contradictions, orphan files, orphan folders, dangling typed edges, summary version, missing closets |
| `/memex:resummarize` | Refresh manifest + hub summaries to current retrieval-tuned format |
| `/memex:reindex` | Backfill or rebuild every hub's `_CLOSETS.md` (and `memory/_CLOSETS.md`) |
| `/memex:consolidate` | Dedup, decisions contradictions, orphan check, decisions compression (independent of session-end) |
| `/memex:search` | Cross-hub search within the current workspace |
| `/memex:link-workspace` | Register the current workspace in the global source registry |
| `/memex:unlink-workspace` | Deregister a workspace from the global source registry |
| `/memex:cross-search` | Grep across linked workspaces' manifests + closets |

## How it works

`_MANIFEST.md` at the workspace root is a routing map. It tells Claude what files exist, which tier they belong to, and what each domain hub is. Per-hub `_CLOSETS.md` files extend that with typed-field summaries of every file's distinct subjects, named entities, decisions, and dates, so Claude can decide which 0-2 files a question actually needs without opening 12.

The `memory/` folder holds always-loaded files: `status.md`, `session-log.md`, `decisions.md`, `glossary.md`, kept small so loading them doesn't burn context. `memory/_CLOSETS.md` adds typed-field retrieval over those.

Domain folders hold actual work. Claude only reads domain files when a task requires them.

Convention over configuration: files in standard locations are found automatically. No config required unless your workspace uses non-standard paths.

## Requirements

- Cowork (Claude desktop app) or Claude Code
- A workspace folder

## License

MIT
