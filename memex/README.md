# Memex

Structured memory for Claude. Gives Claude persistent context across sessions so it starts every conversation already oriented - not starting from scratch.

## What it does

- **Tiered context loading** - Tier 1 files load every session; Tier 2 loads on demand; Tier 3 is archived. Claude only reads what it needs.
- **Session briefings** - every session opens with a status summary, blockers, in-flight work, and ideas from the inbox
- **Session close** - memory files update automatically, decisions get logged, wikilinks get verified
- **Ideas inbox** - capture thoughts mid-session without breaking flow
- **Obsidian-compatible** - workspace files use `[[wikilink]]` format and work with [Obsidian](https://obsidian.md/)

## Quick start

1. Open a Cowork session in your workspace
2. Type `/memex:init`
3. Done. Future sessions auto-brief via the session hook.

Empty workspace? Init scaffolds everything in under 30 seconds, zero questions. Existing files? Init scans and wires them into a manifest without moving anything.

## Skills

| Skill | What it does |
|-------|-------------|
| `/memex:init` | Set up, adopt, health-check, or upgrade a workspace |
| `/memex:session-start` | Briefing at session open |
| `/memex:session-end` | Close cleanly - update memory, log decisions, verify links |
| `/memex:update` | Mid-session flush - save status without closing |
| `/memex:idea` | Quick-capture an idea to the inbox |
| `/memex:add-domain` | Add a new domain folder with hub index |
| `/memex:archive` | Move a file from active to archived in the manifest |
| `/memex:wikilinks` | Check for broken links and convert plain text references to `[[wikilinks]]` |
| `/memex:lint` | Audit workspace health: stale status, contradictions, orphans |

## How it works

Memex creates a `_MANIFEST.md` file in your workspace root. This is a routing map - it tells Claude what files exist, which tier they belong to, and what each domain hub is. Claude reads this at the start of every session to know what to load.

The `memory/` folder holds small, always-loaded files: `status.md`, `session-log.md`, `decisions.md`, `glossary.md`. These are kept small so loading them doesn't burn context.

Domain folders hold your actual work. Claude only reads domain files when a task requires it.

Memex uses convention over configuration. Files in standard locations (`memory/`, `scratch/`) are found automatically. No configuration required unless your workspace uses non-standard paths.

## Requirements

- Cowork (Claude desktop app) or Claude Code
- A workspace folder

## License

MIT
