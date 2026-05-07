# Memex

**Structured memory for Claude Cowork. Pick up where you left off.**

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Recall](https://img.shields.io/badge/LongMemEval--S%20R%405-90.1%25-brightgreen)

> **90.1% Recall@5 on [LongMemEval-S](https://huggingface.co/datasets/xiaowu0162/longmemeval)** (Wu et al., ICLR 2025) — the published retrieval benchmark for long-term memory in chat assistants. Measured, reproducible in 3-5 minutes, $0. [Details below.](#validated-retrieval-quality)

---

## The Problem

Cowork sessions are stateless. You open a new session and Claude has no idea what you were doing yesterday. You spend the first 10 minutes re-explaining context. Decisions from three sessions ago? Gone.

Cowork Projects gives you persistent files, but files without a system is just a folder full of stuff. Claude doesn't know what to read, what's stale, or what matters right now.

## The Solution

Memex converts your workspace into a connected knowledge system with persistent memory, tiered context loading, full `[[wikilink]]` navigation, a temporal facts model, and cross-workspace federation — all in pure markdown with zero runtime dependencies.

- **Wikilinked knowledge base.** Every file reference becomes a `[[wikilink]]`. Your workspace builds into a connected graph over time. Open it in [Obsidian](https://obsidian.md/) to see how everything relates visually.
- **Two-tier index.** A `_MANIFEST.md` plus per-hub `_CLOSETS.md` files mean Claude knows what every file contains *without opening any of them*. Massive recall improvements on questions about specific subjects, not just topics.
- **Temporal facts.** A SQLite sidecar (Python stdlib only) tracks subject-predicate-object facts with `valid_from` / `valid_to` dates, so when something changes — Mike got promoted, the office moved, the spring campaign was cancelled — the old fact gets stamped, not overwritten. Contradiction detection catches drift automatically.
- **Typed-edge graph.** Optional YAML frontmatter (`supersedes`, `blocks`, `people`, `projects`) builds a typed knowledge graph at session-end. Zero LLM calls; pure regex.
- **Cross-workspace federation.** Register multiple workspaces (nonprofit, personal, work) in a global registry and search across all of them with `/memex:cross-search`. Privacy-first: opt-in per source.
- **Standalone consolidation cycle.** `/memex:consolidate` runs dedup, contradiction sweep, and orphan check independently from session-end, so a session timeout doesn't compound drift.
- **Convention over configuration.** Drop files in standard locations and they just work. No config tables to maintain.
- **Zero dependencies.** Markdown files plus stdlib Python. No database server, no API keys, no embeddings backend, no cloud.

### Validated retrieval quality

Memex is benchmarked on [LongMemEval-S](https://huggingface.co/datasets/xiaowu0162/longmemeval) (Wu et al., ICLR 2025), the standard benchmark for long-term memory in chat assistants. R@5 is the share of questions where the top-5 retrieved sessions include a ground-truth answer session.

| Metric | Memex (`closets:emax`) |
|---|---|
| **Recall@5** | **90.1%** |
| Recall@10 | 94.6% |
| Hit@5 | 96.4% |
| MRR | 0.880 |

500 questions. Within 0.5pp of `content:bm25` (the upper bound that indexes the entire raw session text), at roughly 1/10th the size — because closets are typed and structured, not raw transcripts. Reproduce in 3-5 minutes with `python benchmarks/longmemeval/run_bench.py --strategies closets:emax`. Full harness and per-category breakdown in [`benchmarks/longmemeval/`](benchmarks/longmemeval/).

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

### The Session Lifecycle

```
SESSION START
  /memex:session-start runs automatically
  Reads status, log, decisions, ideas
  Gives you a 20-second briefing
  "What are we working on today?"

DURING SESSION
  Work normally. Claude reads hub files as needed.
  Capture ideas with /memex:idea.
  Save progress mid-session with /memex:update.

SESSION END
  /memex:session-end runs automatically
  Updates status.md, writes session-log entry
  Updates touched hub files, logs decisions
  Checks wikilink integrity
  Prints confirmation
```

### File Structure

After setup, your workspace looks like this:

```
your-workspace/
├── CLAUDE.md              # Project identity + Memex invocation lines
├── _MANIFEST.md           # Context routing map (Tier 1 / 2 / 3)
├── memory/
│   ├── status.md          # What's happening right now (VOLATILE)
│   ├── session-log.md     # Rolling handoff log (VOLATILE)
│   ├── decisions.md       # Key decisions logged as claims (STABLE)
│   └── glossary.md        # Project-specific terms (STABLE)
├── [domain folders]/
│   └── [domain]-index.md  # Hub file for each domain (Tier 2)
└── scratch/
    └── ideas.md           # Raw idea inbox (VOLATILE)
```

### Tiered Context Loading

| Tier | When loaded | Files |
|------|------------|-------|
| **Tier 1** | Every session | `status.md`, `session-log.md`, `decisions.md`, `glossary.md`, `ideas.md` |
| **Tier 2** | When working in that area | Domain hub files, then individual files as needed |
| **Tier 3** | Only if you ask | Completed or superseded docs |

---

## Skills

| Skill | What it does |
|-------|-------------|
| `/memex:init` | Set up, adopt, health-check, or upgrade a workspace |
| `/memex:upgrade` | One-command v1→v2 migration: orchestrates resummarize + reindex + lint, idempotent on re-run |
| `/memex:session-start` | Briefing at session open |
| `/memex:session-end` | Close cleanly: update memory, log decisions, refresh closets, verify links + graph |
| `/memex:update` | Mid-session flush: save status without closing |
| `/memex:idea` | Quick-capture an idea to the inbox |
| `/memex:add-domain` | Add a new domain folder with hub index and closets file |
| `/memex:archive` | Move a file from active to archived in the manifest |
| `/memex:wikilinks` | Check for broken links and convert plain text references to `[[wikilinks]]` |
| `/memex:lint` | Audit workspace health: stale status, contradictions, orphans, dangling typed edges, summary version |
| `/memex:resummarize` | Refresh manifest + hub summaries to v2 retrieval-tuned format |
| `/memex:reindex` | Backfill or rebuild every hub's `_CLOSETS.md` from underlying file content |
| `/memex:facts` | Query, add, or reconcile temporal facts in the SQLite knowledge graph |
| `/memex:consolidate` | Run dedup, contradiction sweep, and orphan check (independent of session-end) |
| `/memex:link-workspace` | Register the current workspace in the global source registry |
| `/memex:unlink-workspace` | Deregister a workspace from the global source registry |
| `/memex:cross-search` | Grep across linked workspaces' manifests + closets, plus query each source's facts.db |

---

## Where to Put Files

Memex doesn't impose a strict folder structure. Here's the convention:

- **Project docs go in domain folders.** One folder per area of work (e.g., `marketing/`, `product/`, `fundraising/`). Each domain folder has a hub file (`[domain]-index.md`) that lists what's inside.
- **Run `/memex:add-domain` to create a domain.** Or just create a folder with a `-index.md` file. Memex detects new domains automatically at session start and session end.
- **Memory files stay in `memory/`.** Status, session log, decisions, glossary. These are always small and always loaded.
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

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions and intentional non-features. The v2 feature set — closets two-tier index, temporal facts SQLite sidecar, typed-edge graph, cross-workspace federation — is summarized in [CHANGELOG.md](CHANGELOG.md#200---2026-05-05).

## Benchmarks

Reproducible retrieval benchmark on LongMemEval-S in [benchmarks/longmemeval/](benchmarks/longmemeval/). Five extractors (content / summary / firstmsg / closets / haiku) × eight rankers (BM25, single-vector embed, multi-vector pools, RRF fusions, ensemble) × 500 questions × six question categories, with paired-bootstrap confidence intervals via `compare.py`. Free, deterministic, runs in 3-5 minutes for the headline. The headline strategy `closets:emax` lands at **90.1% R@5** — within 0.5pp of the full-text upper bound at ~10× smaller representation.

## Contributing

MIT license. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Inspiration

- [Vannevar Bush, "As We May Think" (1945)](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/)

## License

MIT. See [LICENSE](LICENSE).
