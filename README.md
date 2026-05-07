# Memex

**Structured memory for Claude Cowork. Pick up where you left off.**

![Version](https://img.shields.io/badge/version-2.1.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> Persistent memory across Cowork sessions in pure markdown. The closets-format index matches full-content keyword search on retrieval recall at roughly 1/10th the size, with zero external dependencies. No database, no API keys, no embeddings backend.

---

## The Problem

Cowork sessions are stateless. You open a new session and Claude has no idea what you were doing yesterday. You spend the first 10 minutes re-explaining context. Decisions from three sessions ago? Gone.

Cowork Projects gives you persistent files, but files without a system is just a folder full of stuff. Claude doesn't know what to read, what's stale, or what matters right now.

## The Solution

Memex converts your workspace into a connected knowledge system with persistent memory, tiered context loading, full `[[wikilink]]` navigation, and cross-workspace federation. All in pure markdown with zero runtime dependencies.

- **Wikilinked knowledge base.** Every file reference becomes a `[[wikilink]]`. Your workspace builds into a connected graph over time. Open it in [Obsidian](https://obsidian.md/) to see how everything relates visually.
- **Two-tier index.** A `_MANIFEST.md` plus per-hub `_CLOSETS.md` files (and `memory/_CLOSETS.md` for Tier 1) mean Claude knows what every file contains *without opening any of them*. Field-level retrieval (subjects, people, claims, decisions, dates, status) on questions about specific subjects, not just topics.
- **Typed-edge graph.** Optional YAML frontmatter (`supersedes`, `blocks`, `people`, `projects`) builds a typed knowledge graph. Zero LLM calls; pure regex.
- **Cross-workspace federation.** Register multiple workspaces (nonprofit, personal, work) in a global registry and search across all of them with `/memex:cross-search`. Privacy-first: opt-in per source.
- **Cross-hub search within a workspace.** `/memex:search` greps the manifest plus every closets file, grouped by folder.
- **Standalone consolidation cycle.** `/memex:consolidate` runs dedup, decisions contradictions, orphan check, and decisions compression independently from session-end, so a session timeout doesn't compound drift.
- **Convention over configuration.** Drop files in standard locations and they just work. No config tables to maintain.
- **Zero dependencies.** Markdown files plus stdlib Python. No database server, no API keys, no embeddings backend, no cloud.

### Retrieval benchmark

Reproducible on [LongMemEval-S](https://github.com/xiaowu0162/LongMemEval) (Wu et al., ICLR 2025). The closets-format index hits **90.1% Recall@5** with the `closets:emax` strategy, within 0.5pp of `content:bm25` (the upper bound that indexes the entire raw session text) at roughly 1/10th the size. 500 questions, free, deterministic, runs in 3-5 minutes:

```
python benchmarks/longmemeval/run_bench.py --strategies closets:emax
```

See [`benchmarks/longmemeval/`](benchmarks/longmemeval/) for the harness, ablations, per-category breakdown, and the full retrieval-vs-QA-accuracy context.

---

## Install

**Requires [Claude Cowork](https://claude.ai/download).** (Can also be adapted for [Claude Code](docs/claude-code-usage.md).)

1. Add the Memex marketplace. Either method works:
   - **Cowork UI:** Click Customize > Browse plugins > "+" to add marketplace. Enter `Skyfox-io/Memex` and click Sync.
   - **Slash command:** Type `/plugin marketplace add Skyfox-io/Memex` in any session.

   (`Skyfox-io/Memex` is GitHub shorthand for `github.com/Skyfox-io/Memex`.)

2. Install the plugin when prompted
3. Run `/memex:init` in your workspace

**New workspace?** Init asks what you're working on, then scaffolds everything in under 30 seconds.

**Existing files?** Init scans your workspace, shows you what it found, and wires everything into a manifest without moving files.

**Already have a memory system?** Init detects existing manifests and operates in compatible mode.

### After setup

Start a new Cowork session. Claude briefs you automatically and asks what you're working on.

If you use [Obsidian](https://obsidian.md/), open the same workspace folder as a vault. All the `[[wikilinks]]` light up in the graph view.

---

## How It Works

### Closets, the typed-field index

Each domain has a `_CLOSETS.md` file (and `memory/_CLOSETS.md` covers Tier 1) that enumerates every file's distinct subjects, named entities, claims, decisions, and dates. Sessions scan closets to pick which 0-2 files a question actually needs, without opening any of them.

Sample closets entry:

```
## [[campaign-plan]]
- subjects: spring fundraising, gala, donor outreach
- people: [[Mike]], [[Jasmine]]
- claims: "raised $42K so far"
- decisions: switched from HubSpot to Anchor on 2026-03-18
- dates: 2026-04-15 (gala)
- status: active
```

A "what about Mike?" question hits the `people:` line. "When did we leave HubSpot?" hits `decisions:`. The model never opens `campaign-plan.md` until the task actually needs the file's full content. That's the moat behind the retrieval benchmark.

Each `_CLOSETS.md` is capped at 30 entries (most-recently-modified files); overflow spills to a sibling `_CLOSETS-archive.md` that loads only on a primary-closets miss. `memory/_CLOSETS.md` does not paginate (Tier 1 is a small fixed set).

### The session lifecycle

```
SESSION START
  /memex:session-start runs automatically
  Reads status, session-log, decisions, ideas, memory/_CLOSETS.md
  Pre-loads the relevant domain's _CLOSETS.md
  Gives you a 30-second briefing
  Asks: "What are we working on today?"

DURING SESSION
  Work normally. Claude consults closets to decide which files to open.
  Capture ideas with /memex:idea.
  Save progress mid-session with /memex:update.
  Cross-hub queries: /memex:search.

SESSION END
  /memex:session-end runs automatically
  Updates status.md (idempotent: skips no-op writes)
  Appends session-log entry
  Refreshes _CLOSETS.md for touched hubs and memory/_CLOSETS.md
  Logs decisions
  Verifies wikilinks; suggests conversions for files modified this session
  Prints confirmation
```

Workspace-wide maintenance (typed-edge graph rebuild, dedup, contradiction sweep, decisions compression) is decoupled from session-end and lives in `/memex:reindex` and `/memex:consolidate`.

### File structure

After setup, your workspace looks like this:

```
your-workspace/
├── CLAUDE.md                # Project identity + Memex invocation lines
├── _MANIFEST.md             # Context routing map (Tier 1 / 2 / 3)
├── memory/
│   ├── status.md            # What's happening right now (VOLATILE)
│   ├── session-log.md       # Rolling handoff log (VOLATILE)
│   ├── decisions.md         # Dated decisions, append-only (STABLE)
│   ├── glossary.md          # Project-specific terms (STABLE)
│   ├── _CLOSETS.md          # Typed-field index over Tier 1 files
│   └── .graph.md            # Typed-edge graph (regenerable, opt-in)
├── [domain]/
│   ├── _CLOSETS.md          # Typed-field index for the domain (Tier 2)
│   ├── _CLOSETS-archive.md  # Overflow above 30 entries (loads on miss)
│   ├── [domain]-index.md    # Optional prose hub (working agreements, etc.)
│   └── ...                  # Actual content files
└── scratch/
    └── ideas.md             # Raw idea inbox (VOLATILE)
```

The `[domain]-index.md` prose hub is optional in v2.1+. Closets-only domains are the default. Add a prose index when you have working-agreement or philosophy text that doesn't fit typed rows.

### Tiered context loading

| Tier | When loaded | Files |
|------|------------|-------|
| **Tier 1** | Every session | `status.md`, `session-log.md`, `decisions.md`, `glossary.md`, `ideas.md`, `memory/_CLOSETS.md` |
| **Tier 2** | When working in that area | Domain `_CLOSETS.md`, then individual files as needed |
| **Tier 3** | Only if you ask | Completed or superseded docs, plus `_CLOSETS-archive.md` for paginated hubs |

Closets are pointers, not load triggers. Listing 12 files in `_CLOSETS.md` does not mean Claude opens 12 files; it means Claude knows what's in each before deciding which 0-2 the current task actually requires.

---

## Skills

| Skill | What it does |
|-------|-------------|
| `/memex:init` | Set up, adopt, health-check, or upgrade a workspace |
| `/memex:upgrade` | One-command migration orchestrator (v1→v2, v2.0→v2.1, future versions); idempotent on re-run |
| `/memex:session-start` | Briefing at session open |
| `/memex:session-end` | Close cleanly: update memory, log decisions, refresh closets, verify links |
| `/memex:update` | Mid-session flush: save status without closing |
| `/memex:idea` | Quick-capture an idea to the inbox |
| `/memex:add-domain` | Add a new domain folder with closets (hub index optional) |
| `/memex:archive` | Move a file from active to archived in the manifest |
| `/memex:wikilinks` | Check for broken links and convert plain text references to `[[wikilinks]]` |
| `/memex:lint` | Audit workspace health: stale status, decision supersession contradictions, orphan files, orphan folders, dangling typed edges, summary version, missing closets |
| `/memex:resummarize` | Refresh manifest + hub summaries to current retrieval-tuned format |
| `/memex:reindex` | Backfill or rebuild every hub's `_CLOSETS.md` (and `memory/_CLOSETS.md`) |
| `/memex:consolidate` | Run dedup, decisions contradictions, orphan check, decisions compression (independent of session-end) |
| `/memex:search` | Cross-hub search within the current workspace: grep manifest + every `_CLOSETS.md`, grouped by folder |
| `/memex:link-workspace` | Register the current workspace in the global source registry |
| `/memex:unlink-workspace` | Deregister a workspace from the global source registry |
| `/memex:cross-search` | Grep across linked workspaces' manifests + closets |

---

## Where to Put Files

Memex doesn't impose a strict folder structure. Here's the convention:

- **Project docs go in domain folders.** One folder per area of work (e.g., `marketing/`, `product/`, `fundraising/`). Each domain folder has a `_CLOSETS.md` typed-field index. An optional `[domain]-index.md` prose hub can also live there for working agreements / philosophy text.
- **Run `/memex:add-domain` to create a domain.** Memex detects new domains automatically at session start and session end.
- **Memory files stay in `memory/`.** Status, session log, decisions, glossary, plus `memory/_CLOSETS.md` for typed-field retrieval over them. These are always small and always loaded.
- **Ideas go in `scratch/ideas.md`.** Capture now, route later. Session-end will remind you about unrouted ideas.
- **Don't worry about getting it perfect.** Start with files wherever they are. Memex wires what exists. Reorganize later as patterns emerge.

---

## Examples

Two fully populated example workspaces in `examples/`:

| Example | Scenario | What's inside |
|---------|----------|---------------|
| `examples/nonprofit/` | Bright Future Foundation, ED managing programs and spring fundraising | 2 domains (programs, fundraising), seeded status, decisions, glossary |
| `examples/startup/` | DashFlow, pre-launch SaaS founder juggling product, GTM, and fundraising | 3 domains (product, go-to-market, fundraising), seeded with MVP priorities |

---

## Wikilinks and Obsidian

Memex converts your workspace into a `[[wikilinked]]` knowledge base. Every file reference Claude writes uses `[[filename]]` format: hub tables, the manifest, status updates, session logs, decisions. When you run `/memex:init` on an existing workspace, Memex also scans your files and converts plain text references to wikilinks.

Your workspace is a connected graph from day one. As you work across sessions, the connections grow.

### Why wikilinks matter

- **For Claude:** Wikilinks tell Claude which files are related. When it reads a hub that says `[[campaign-plan]]`, it knows that file exists and can load it if needed.
- **For you:** Wikilinks make your knowledge base navigable. Click a link, jump to that file. See what links to what.
- **For persistence:** When files move or get renamed, wikilinks get updated across the workspace. The graph stays connected.

### Using Obsidian

[Obsidian](https://obsidian.md/) reads `[[wikilinks]]` natively. Open your workspace folder as an Obsidian vault and you get:

- **Graph view** (Cmd+G / Ctrl+G). Visual map of your entire workspace. Memory files cluster together, domain hubs connect to their files, everything visible at a glance.
- **Click-through navigation.** Every `[[wikilink]]` is clickable. Jump from the manifest to a hub to an individual file.
- **Backlinks panel.** See what references the current file. Useful for understanding which decisions affect which domains.
- **Color-coded domains.** Group files by folder in graph settings to see domain clusters.
- **Full-text search.** Search across everything, including archived Tier 3 files that Claude doesn't load by default.

[Obsidian](https://obsidian.md/) is optional. The wikilink system works without it since Claude reads the links directly. But if you want to see and navigate your knowledge base visually, it's the recommended companion.

See [docs/obsidian-setup.md](docs/obsidian-setup.md) for detailed setup instructions.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions and intentional non-features. The v2.1 feature set (closets two-tier index, typed-edge graph, cross-workspace federation, within-workspace cross-hub search) is summarized in [CHANGELOG.md](CHANGELOG.md).

## Benchmarks

Reproducible retrieval benchmark on LongMemEval-S in [benchmarks/longmemeval/](benchmarks/longmemeval/). Five extractors (content / summary / firstmsg / closets / haiku) × eight rankers (BM25, single-vector embed, multi-vector pools, RRF fusions, ensemble) × 500 questions × six question categories, with paired-bootstrap confidence intervals via `compare.py`. Free, deterministic, runs in 3-5 minutes for the headline. The headline strategy `closets:emax` lands at **90.1% R@5**, within 0.5pp of the full-text upper bound at ~10× smaller representation.

## Contributing

MIT license. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Inspiration

- [Vannevar Bush, "As We May Think" (1945)](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/)

## License

MIT. See [LICENSE](LICENSE).
