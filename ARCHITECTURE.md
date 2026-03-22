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

Memex is a Claude Cowork plugin with 8 skills:

| Skill | Purpose |
|-------|---------|
| `init` | Set up, adopt, health-check, or upgrade |
| `session-start` | Session briefing |
| `session-end` | Session close |
| `update` | Mid-session memory flush |
| `idea` | Quick idea capture |
| `add-domain` | Add domain folder with hub and file organization |
| `archive` | Move file to Tier 3 |
| `wikilinks` | Check broken links + convert plain text to wikilinks |

Skills are namespaced under `memex:`. Hooks fire `session-start` and `session-end` automatically. CLAUDE.md contains three lines: session-start invocation, session-end invocation, and wikilink format rule. All logic lives in the skills.

---

## Intentional Non-Features

- **No database.** Markdown is the storage layer.
- **No MCP server.** No running process needed.
- **No semantic search.** Hub-and-spoke with manifest summaries handles relevance.
- **No cross-workspace memory.** Each workspace is self-contained.
- **No GUI.** The visual layer is [Obsidian](https://obsidian.md/).
- **No automatic archival.** Session-end surfaces candidates at milestones. The user decides.

---

## Design Principles

1. **Context is currency.** Load the minimum needed for the current task.
2. **Convention over configuration.** Standard paths work out of the box.
3. **The system maintains itself.** Users don't do bookkeeping.
4. **Markdown is the interface.** Human-readable, version-controllable, [Obsidian](https://obsidian.md/)-compatible.
5. **Progressive disclosure.** Load the index first. Drill down only if needed.
6. **Never assume, never delete.** Init proposes organization, moves only with confirmation, archives originals of migrated files.
