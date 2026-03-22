# Memex Architecture

Design decisions behind Memex, what it does and doesn't do, and why.

---

## Core Model: Structured Memory via Markdown

Memex is a file-based memory system. No database, no server, no runtime. The workspace is a directory of markdown files organized into three layers:

1. **Memory layer** (`memory/`) - Session-volatile state: what's happening now, what happened last time, what decisions constrain the work
2. **Domain layer** - Domain-organized project files with hub indexes for navigation. Domains live wherever makes sense for the workspace.
3. **Routing layer** (`_MANIFEST.md`) - Context routing map that tells Claude what to load and when

The filesystem is the query engine. Navigation happens through `[[wikilinks]]` and hub files, not search queries.

---

## Convention Over Configuration

Memex resolves file paths using a three-step chain:

1. **Config table** in `_MANIFEST.md` (if present, use its values)
2. **Convention** (standard locations: `memory/status.md`, `scratch/ideas.md`, etc.)
3. **Search** (find the file by name in the workspace)

This means a user who drops `status.md` into `memory/` gets a working system without any configuration. Config is optional, not required. Only needed when files live in non-standard locations.

---

## Tiered Context Loading

The most important design decision is **not loading everything**. Claude's context window is finite. Every token spent on context is a token unavailable for work.

### Tier 1 - Always Load
Files read every session: `status.md`, `session-log.md`, `decisions.md`, `glossary.md`, `ideas.md`.

Kept deliberately small:
- `status.md` is prune-only - completed items are removed, not moved
- `session-log.md` caps at 10 entries - oldest get archived
- `decisions.md` stays under 100 lines - related entries get compressed

### Tier 2 - Load by Domain
Domain hub files load when the task touches that domain. Individual files load only when the hub indicates they're needed. **Progressive disclosure applied to context.**

### Tier 3 - Archival
Complete or superseded files. They exist on disk but Claude never loads them unless asked. Moving files to Tier 3 is a first-class operation (`/memex:archive`).

---

## Three-Tier Workspace Detection

Memex adapts to what it finds:

| What exists | Behavior |
|-------------|----------|
| Manifest with `<!-- memex-managed -->` marker | Full Memex mode |
| Manifest with Tier 1/2/3 structure, no marker | Compatible mode - operates session lifecycle without requiring migration |
| No manifest | Prompts user to run `/memex:init` |

This lets Memex adopt existing workspaces without requiring structural changes.

---

## Two-Track Init

Init adapts to workspace state:

- **Track A (empty workspace):** Ask one question ("What are you working on?"), then scaffold everything in under 30 seconds. Memory files seeded with a real answer, ideas inbox, manifest, CLAUDE.md lines. Done.
- **Track B (existing files):** Scan file content, suggest domain groupings, propose file moves with confirmation, build manifest and hubs. Four visible steps: scan, analyze, propose, build.

The manifest writes last. It's the activation marker - the system is not live until everything else is in place.

---

## Session Management

### Session Start (`/memex:session-start`)
Reads Tier 1 files, outputs a structured briefing designed to be read in 30 seconds. Only surfaces what's actionable. Also scans for untracked content (files and folders not in any hub) and suggests organizing them. This catches new files users created between sessions or in archived sessions that never ran session-end.

### Session End (`/memex:session-end`)
Executes without asking permission between steps:
1. Update status.md
2. Write session-log entry
3. Update touched hub files (including informally created domains)
4. Log decisions
5. Verify wikilinks
6. Output confirmation with ideas inbox count as FYI

**The user works, the system maintains itself.**

---

## Skill Architecture

Memex is a Claude plugin with 8 skills:

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

Skills are namespaced under `memex:`. Hooks fire `session-start` and `session-end` automatically. CLAUDE.md contains only two invocation lines - all logic lives in the skills.

---

## Wikilink Integrity

Every `[[wikilink]]` must resolve to an existing file. The wikilinks script runs at every session end and can be invoked standalone with `/memex:wikilinks`. It does two things: checks for broken links (target: zero), and finds plain text file references that should be converted to `[[wikilinks]]`. Init also runs the conversion pass when adopting existing workspaces.

---

## Intentional Non-Features

- **No database.** Markdown is the storage layer.
- **No MCP server.** No running process needed.
- **No semantic search.** Hub-and-spoke handles relevance.
- **No cross-workspace memory.** Each workspace is self-contained.
- **No GUI.** The dashboard is [Obsidian](https://obsidian.md/), VS Code, or `cat status.md`.
- **No auto-domain detection.** Let users name their domains.
- **No automatic archival suggestions.** Let session-end surface candidates at milestones.

---

## Design Principles

1. **Context is currency.** Load the minimum needed for the current task.
2. **Convention over configuration.** Standard paths work out of the box.
3. **The system maintains itself.** Users don't do bookkeeping.
4. **Markdown is the interface.** Human-readable, version-controllable, [Obsidian](https://obsidian.md/)-compatible.
5. **Progressive disclosure.** Load the index first. Drill down only if needed.
6. **Never assume, never delete.** Init wires what exists, creates what's missing, moves nothing.
