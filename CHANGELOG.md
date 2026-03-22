# Changelog

## [1.0.0] - 2026-03-21

Initial public release as a Claude plugin.

### Core Features

- **Wikilinked knowledge base.** Converts workspaces into a connected `[[wikilink]]` graph. Init scans existing files and converts plain text references. All skills enforce wikilink format. Obsidian-compatible out of the box.
- **Tiered context loading.** Tier 1 (always load), Tier 2 (by domain), Tier 3 (archived). Claude only reads what it needs. Volatility markers (VOLATILE/STABLE) control freshness.
- **Two-track init.** Empty workspace: one question, 30-second scaffold. Existing files: content-aware scan, suggest domains, propose file moves, wire manifest. Zero file deletions.
- **Convention over configuration.** Standard paths (`memory/`, `scratch/`) work out of the box. Config optional for non-standard layouts. Path resolution: config > convention > search.
- **Three-tier workspace detection.** Memex-managed (full features), compatible (existing manifest without marker), none (prompt to init). Adopts existing workspaces without migration.
- **Session automation.** Hooks auto-trigger session-start and session-end. Single-line hook prompts, all logic in skills.
- **Content-aware scanning.** Session-start and session-end scan for untracked folders and loose files, suggest domain organization based on file content.

### Skills (8)

| Skill | Purpose |
|-------|---------|
| `init` | Set up, adopt, health-check, or upgrade a workspace |
| `session-start` | Session briefing with status, blockers, ideas, untracked content |
| `session-end` | Update memory, log decisions, verify wikilinks, detect domains |
| `update` | Mid-session memory flush without closing |
| `idea` | Quick-capture to ideas inbox (auto-creates if missing) |
| `add-domain` | Add domain folder with hub, scan for related files |
| `archive` | Move file from Tier 2 to Tier 3 |
| `wikilinks` | Check broken links and convert plain text to `[[wikilinks]]` |

### Plugin System

- Distributed via Claude plugin marketplace (`/plugin marketplace add Skyfox-io/Memex`)
- `SessionStart` and `SessionEnd` hooks for automatic session lifecycle
- `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` for portable path references
- Versioned manifest marker (`<!-- memex-managed:1.0.0 -->`) for upgrade detection
