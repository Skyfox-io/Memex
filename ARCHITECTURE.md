# Memex Architecture

Design decisions behind Memex, what it does and doesn't do, and why.

---

## Core Model: Structured Memory via Markdown

Memex is a file-based memory system for Claude Cowork. No database, no server, no runtime. The workspace is a directory of markdown files organized into three layers:

1. **Memory layer** (`memory/`) - Session-volatile state: what's happening now, what happened last time, what decisions constrain the work
2. **Domain layer** - Domain-organized project files with hub indexes for navigation. Domains live wherever makes sense for the workspace.
3. **Routing layer** (`_MANIFEST.md`) - Context routing map that tells Claude what to load and when. Every file entry includes a one-line content summary so Claude can scan the manifest and decide what to open without reading every file.

The filesystem is the query engine. Navigation happens through `[[wikilinks]]` and hub files, not search queries.

---

## Hub-and-Spoke Token Efficiency

The manifest knows everything. Claude reads the minimum.

The hub-and-spoke architecture gives Claude full awareness of the workspace while only loading what the current task needs. The manifest lists every file with a summary. Hub indexes list every file in a domain. But Claude only opens the files it actually needs for the current task. This keeps token costs low and context quality high across sessions of any size.

Wikilinks are pointers, not load triggers. Seeing `[[brand-voice]]` in a file tells Claude that file exists. It doesn't mean Claude should open it unless the task requires it.

---

## Closets Two-Tier Index

The manifest summarises *what's in the workspace*. The per-hub `_CLOSETS.md` files summarise *what's in each file*, in a typed-field format an LLM can scan field-by-field.

Each `<domain>/_CLOSETS.md` entry has up to six lines:

```
## [[file-stem]]
subjects: <distinct subjects enumerated, mid-file mentions included>
people:   <named entities as [[wikilinks]]>
claims:   <verbatim user-stated facts: "allergic to coffee", "I'm a teacher">
decisions: <reversal verbs: switched / abandoned / picked over>
dates:    <YYYY-MM-DD mentions, even relative dates resolved to absolute>
status:   active | archived | superseded
```

This is the moat. A question like "what about Mike?" matches `people:`; "when did I switch to Linear?" matches `decisions:` + `dates:`; "what did I tell you about my allergies?" matches `claims:`. Each typed field is independently retrievable by an LLM's attention. On [LongMemEval-S](https://github.com/xiaowu0162/LongMemEval), this representation hits **90.1% R@5**, within 0.5pp of indexing the full raw transcript, at roughly 1/10th the size.

Pagination engages at 30 entries: the most-recently-modified files stay in `_CLOSETS.md`; older entries spill to a sibling `_CLOSETS-archive.md` that session-start does **not** load eagerly. The archive is the fallback when the primary closets file lacks a match for the user's question.

Format spec: [`memex/skills/session-end/references/closets-format.md`](memex/skills/session-end/references/closets-format.md). Summary-writing rules (8 retrieval-tuned rules, benchmark-validated): [`memex/skills/session-end/references/summary-rules.md`](memex/skills/session-end/references/summary-rules.md).

---

## Temporal Facts SQLite Sidecar

Some facts have a clock attached: where Alice works *now* vs *in 2024*; the spring campaign budget *before* legal flagged it. Markdown alone can't represent that without losing the timeline.

`memory/.facts.db` is a stdlib `sqlite3` database storing `(subject, predicate, object)` triples with `valid_from` (always set) and `valid_to` (`NULL` = currently valid). Supersession closes the old row and inserts a new one with the same subject+predicate. Contradiction detection surfaces any `(subject, predicate)` pair with multiple distinct currently-valid objects.

The DB is regenerable. `memory/facts.md` is the human-readable mirror, committed to git. `facts.py rebuild` wipes the DB and reloads from the mirror. If the two drift, the mirror wins.

Surface: [`/memex:facts`](memex/skills/facts/SKILL.md) skill (explicit-invocation only. Autonomous DB writes from model inference would silently insert false facts). Read-side queries flow through the skill or via [`/memex:cross-search`](memex/skills/cross-search/SKILL.md) for cross-workspace lookups.

---

## Typed-Edge Graph

Optional YAML frontmatter on any file (`supersedes`, `superseded-by`, `blocks`, `blocked-by`, `people`, `projects`, `type`, `status`, `date`) is parsed at session-end into `memory/.graph.md`. Pure regex; zero LLM calls; files without frontmatter contribute nothing.

The graph is purely additive. Opt in by adding frontmatter to any file, opt out by removing it. Lint surfaces dangling typed edges (a file references `supersedes: [[old-decision]]` but `old-decision.md` doesn't exist).

Schema: see [CONTRIBUTING.md](CONTRIBUTING.md#frontmatter-schema). Extractor: `memex/scripts/extract-graph.py`.

---

## Cross-Workspace Federation

Multiple Memex workspaces (nonprofit / personal / work) each have their own files; their manifests, closets, and `facts.db` files are *all* searchable from any workspace via `/memex:cross-search`.

Mechanism: `~/.memex/sources.md` is a per-user global registry of `(name, path, registered, searchable)` rows. `/memex:link-workspace` adds the current workspace; `/memex:unlink-workspace` removes it; `/memex:cross-search` greps every registered source's manifest + closets and queries each `memory/.facts.db` read-only. Privacy: each source has a `searchable: true|false` flag for total per-source opt-out.

This federation is opt-in per source and read-only across the boundary. No syncing, no auth, no shared state, just grep + SQL across files the user has explicitly registered.

---

## Convention Over Configuration

Memex resolves file paths using a three-step chain:

1. **Config table** in `_MANIFEST.md` (if present, use its values)
2. **Convention** (standard locations: `memory/status.md`, `scratch/ideas.md`, etc.)
3. **Search** (find the file by name in the workspace)

A user who drops `status.md` into `memory/` gets a working system without any configuration. Config is optional, not required.

---

## Tiered Context Loading

The most important design decision is **not loading everything**. Claude's context window is finite. Every token spent on context is a token unavailable for work.

### Tier 1 - Always Load
Files read every session: `status.md`, `session-log.md` (latest entry only), `decisions.md`, `glossary.md`, `ideas.md`.

Kept deliberately small:
- `status.md` is prune-only - completed items are removed, not moved
- `session-log.md` caps at 10 entries - oldest get archived. Session-start reads only the most recent entry.
- `decisions.md` stays under 100 lines - related entries get compressed

### Tier 2 - Load by Domain
Domain hub files load when the task touches that domain. Individual files load only when the hub indicates they're needed. **Progressive disclosure applied to context.**

### Tier 3 - Archival
Complete, superseded, or stale files. They exist on disk but Claude never loads them unless asked. Moving files to Tier 3 is a first-class operation (`/memex:archive`).

---

## Three-Tier Workspace Detection

Memex adapts to what it finds:

| What exists | Behavior |
|-------------|----------|
| Manifest with `<!-- memex-managed -->` marker | Full Memex mode |
| Manifest with Tier 1/2/3 structure, no marker | Compatible mode - operates session lifecycle without requiring migration |
| No manifest | Prompts user to run `/memex:init` |

---

## Init: Two Paths

Init adapts to workspace state:

- **Empty workspace:** Ask one question ("What are you working on?"), then scaffold everything in under 30 seconds. Memory files seeded with a real answer, ideas inbox, manifest, CLAUDE.md lines. Done.
- **Existing files:** Scan file content, analyze for domain groupings, detect catch-all folders, flag stale or conflicting files, propose organization with file moves, build manifest and hubs with confirmation. Content-aware, not just structure-aware.

The manifest writes last. It's the activation marker.

### Content-Aware Analysis

Init doesn't just read folder structure. It reads file content to:
- Distinguish reference types (glossary vs contacts vs quick refs)
- Detect catch-all folders and recommend dissolving them
- Flag stale files (outdated, deprecated, superseded) for Tier 3
- Surface conflicting files and ask which is authoritative
- Identify cross-domain relationships for lateral wikilinks

---

## Wikilink System

Memex converts workspaces into `[[wikilinked]]` knowledge bases. Every file reference Claude writes uses `[[filename]]` format. This serves two purposes:

1. **For Claude:** Wikilinks tell Claude which files are related and that they exist, without requiring it to open them.
2. **For users:** Open the workspace in [Obsidian](https://obsidian.md/) and every wikilink becomes a clickable edge in the knowledge graph.

### Wikilink Conversion

Init converts existing files in two passes:
- **Pass 1 (automated):** Exact filename matches converted without confirmation
- **Pass 2 (proposed):** Semantic references proposed to the user for confirmation

### Lateral Cross-Linking

After building hubs, init scans for cross-domain references and proposes wikilinks between files in different domains. This turns isolated hub-and-spoke clusters into a connected knowledge web.

### Integrity

The wikilinks script checks for broken links at every session end and can be run standalone. Target is always zero broken links.

---

## Session Management

### Session Start (`/memex:session-start`)
Scans the manifest summaries, reads Tier 1 files (session-log latest entry only), and outputs a structured briefing in 30 seconds. Scans for untracked content and suggests organizing it. This catches files created between sessions or in archived sessions that never ran session-end.

### Session End (`/memex:session-end`)
Executes without asking permission between steps:
1. Update status.md
2. Write session-log entry
3. Update touched hub files (including informally created domains)
4. Scan for untracked domains and loose files
5. Log decisions
6. Verify wikilinks
7. Refresh manifest summaries for changed files
8. Output confirmation with ideas inbox count

**The user works, the system maintains itself.**

---

## Skill Architecture

Memex is a Claude Cowork plugin with 18 skills, split by autonomous-invocation policy:

**Autonomous (model can trigger from a description match):**

| Skill | Purpose |
|-------|---------|
| `session-start` | Session briefing — fires on the SessionStart hook |
| `session-end` | Session close — fires on the SessionEnd hook |
| `update` | Mid-session checkpoint flush |
| `idea` | Quick idea capture to scratch inbox |
| `lint` | Audit workspace structural health (read-only by default) |
| `cross-search` | Read-only grep + facts.db query across linked workspaces |

**Explicit-only (`disable-model-invocation: true`. User must type the slash command):**

| Skill | Purpose |
|-------|---------|
| `init` | Set up, adopt, or health-check a workspace |
| `upgrade` | One-command migration orchestrator (v1→v2, v2.0→v2.1, future versions) |
| `add-domain` | Create a new domain folder with closets (hub index optional) |
| `archive` | Move a file from Tier 2 to Tier 3 |
| `wikilinks` | Verify and bulk-convert plain text references to `[[wikilinks]]` |
| `resummarize` | Refresh manifest + hub summaries to current retrieval-tuned format |
| `reindex` | Backfill or rebuild every hub's `_CLOSETS.md` (and `memory/_CLOSETS.md`) |
| `consolidate` | Independent dedup + contradiction sweep + orphan check + decisions compression |
| `search` | Cross-hub search within the current workspace |
| `facts` | Query, write, supersede, or reconcile temporal facts in the SQLite sidecar |
| `link-workspace` | Register the current workspace in the global source registry |
| `unlink-workspace` | Deregister a workspace from the global source registry |

Skills are namespaced under `memex:`. Hooks fire `session-start` and `session-end` automatically (configured in `memex/hooks/hooks.json`). CLAUDE.md contains three lines: session-start invocation, session-end invocation, and the wikilink format rule. All logic lives in the skills.

Bulk-write skills (`consolidate`, `reindex`, `resummarize`, `upgrade`) share a locking convention. See [`memex/skills/consolidate/references/locking.md`](memex/skills/consolidate/references/locking.md).

---

## Progressive Disclosure in Skills

Skills that handle multiple independent paths use `references/` sub-files to keep the main SKILL.md focused. Claude reads the main file first, then loads references only when the current path requires them.

Currently used by:
- `init`. `references/scan-and-organize.md`, `references/health-check.md`, `references/migrations.md`, `references/post-setup-message.md` (init has four genuinely separable flows)
- `session-end`. `references/closets-format.md` and `references/summary-rules.md` (canonical specs cited by many other skills)
- `consolidate`. `references/locking.md` (genuinely shared by 4 bulk-write skills)
- `cross-search`. `references/registry.md` (shared with link-workspace and unlink-workspace)
- `facts`. `references/cli.md` (exhaustive subcommand surface)
- `upgrade`. `references/v1-to-v2.md` (version-specific migration playbook; future versions add their own)

Linear skills that run every step every time (`session-start`, `update`, `idea`, `archive`, `add-domain`, `link-workspace`, `unlink-workspace`, `lint`, `wikilinks`, `reindex`, `resummarize`) stay as single SKILL.md files. The cohesion pass at v2.0.0 specifically inlined `lint/references/checks.md` and `consolidate/references/phases.md` because the references *were* the skill. That's an upside-down split, not progressive disclosure.

---

## Plugin Data

`$CLAUDE_PLUGIN_DATA` is a stable per-plugin directory that survives skill upgrades. Memex uses it for operational data that isn't workspace content:

- `session-closes.log`. Appended by session-end to track clean closes

This data is best-effort. Skills that write to it skip silently if the variable isn't set. Skills that read from it treat missing data as absent, not as an error.

Workspace-local operational state lives under `memory/` instead:

- `memory/.{consolidate,reindex,resummarize,upgrade}.lock`. Bulk-write locks, 30-minute staleness rule (see [`memex/skills/consolidate/references/locking.md`](memex/skills/consolidate/references/locking.md)). These guard genuine multi-minute write operations; there is no session-level lock (session-end is idempotent and runs unconditionally).
- `memory/.{consolidate,reindex,resummarize,upgrade}-runs.log`. Append-only run logs; session-end reads `.consolidate-runs.log` to nag about cadence.
- `memory/.facts.db`. SQLite temporal facts (regenerable from `memory/facts.md`).
- `memory/.graph.md`. Typed-edge graph (regenerable from frontmatter via `extract-graph.py`). Refreshed lazily by `/memex:reindex` and `/memex:consolidate`, not at session-end.

---

## Gotchas in Skills

Skills with known failure modes include a `## Gotchas` section at the bottom of SKILL.md. These document edge cases, false-positive risks, and session-lifecycle issues that users and contributors should know about.

Gotchas are the highest-signal content for improving skill reliability over time. When a new failure mode is discovered, add it to the relevant skill's gotchas section.

---

## Intentional Non-Features

- **No primary database.** Markdown is the source of truth. The `memory/.facts.db` SQLite sidecar exists only to make temporal queries fast. It's regenerable from the markdown mirror at `memory/facts.md`.
- **No MCP server.** No running process needed.
- **No learned vector index.** No FAISS, no HNSW, no embedding store at runtime. The closets typed-field index handles relevance.
- **No automatic cross-workspace sync.** Federation is opt-in per source and read-only across the boundary. `/memex:cross-search` greps registered workspaces, never writes.
- **No GUI.** The visual layer is [Obsidian](https://obsidian.md/).
- **No automatic archival.** Session-end surfaces candidates at milestones. The user decides.
- **No autonomous DB writes.** `/memex:facts` is gated behind explicit invocation; the model can't silently insert false facts on inference.

---

## Design Principles

1. **Context is currency.** Load the minimum needed for the current task.
2. **Convention over configuration.** Standard paths work out of the box.
3. **The system maintains itself.** Users don't do bookkeeping.
4. **Markdown is the interface.** Human-readable, version-controllable, [Obsidian](https://obsidian.md/)-compatible.
5. **Progressive disclosure.** Load the index first. Drill down only if needed.
6. **Never assume, never delete.** Init proposes organization, moves only with confirmation, archives originals of migrated files.
