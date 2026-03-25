# Changelog

## [1.0.6] - 2026-03-25

### Improved
- Session-start offers "Start session" or "Update first" prompt after briefing, so users can flag work done between sessions without extra friction.
- Session-end checks status sections in touched domain files (Step 5) and updates them if the session's work made them stale.

## [1.0.5] - 2026-03-22

### Improved
- README explains the hub-and-spoke architecture's purpose: full workspace awareness with minimal token cost.

## [1.0.4] - 2026-03-22

### Improved
- Init proposal step now shows the user exactly what will be added to CLAUDE.md before they confirm.
- Init completion output includes a skills table prioritizing session-active skills.
- Session start/end noted as automatic so users know they don't need to invoke them manually.

## [1.0.3] - 2026-03-22

### Improved
- Init distinguishes reference types: term definitions go to glossary, people/contacts/roles become their own Tier 1 file, quick refs stay separate.
- Init detects stale files (outdated, deprecated, superseded, version suffixes) and routes them to Tier 3 instead of active domains.
- Init surfaces conflicting files (same topic, different content) in the proposal step and asks which is authoritative before placing either.

## [1.0.2] - 2026-03-22

### Improved
- Init explains that `_MANIFEST.md` is the central routing file in the proposal step.
- Init recommends Obsidian as a visual layer after completion, with setup instructions.
- Init detects catch-all folders and recommends dissolving them instead of creating hubs.
- Install instructions updated with Cowork UI method alongside slash command.

## [1.0.1] - 2026-03-22

### Improved
- Session-start reads only the latest session-log entry instead of the full file. Stops at the first separator. Handles multiple sessions per day correctly.
- Manifest entries now include one-line content summaries. Session-start scans these to decide what to load without opening every file.
- Wikilink conversion split into two passes: exact filename matches apply automatically, semantic references are proposed to the user for confirmation.
- Init weaves lateral cross-links between files in different domains, enriching the Obsidian graph without affecting tiered loading.
- Session-end refreshes manifest summaries when file content changes.
- Hub Map entries include domain summaries.

## [1.0.0] - 2026-03-21

Initial public release as a Claude Cowork plugin.

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
