# Scan and Organize Flow

> Referenced from the main init skill when a workspace has files but no `_MANIFEST.md`.

## Scan

```bash
find "$WORKSPACE_ROOT" -not -path "*/.git/*" -not -path "*/.claude/*" -not -path "*/.obsidian/*" | head -200
```

Read every markdown file to understand its content and purpose.

## Analyze

Classify each file based on **content**, not folder structure:

- **Memory-like files.** Status tracking, session logs, decision logs, glossaries.
- **Reference types.** Keep separate kinds of reference content separate. Term definitions and shorthand go into `glossary.md`. People directories, contacts, team roles, and access rules become their own Tier 1 file (`memory/contacts.md`). Quick reference sheets stay separate.
- **Ideas-like files.** Existing idea captures, brainstorm docs, inbox files. Content migrates to `scratch/ideas.md`; originals move to Tier 3.
- **Stale or superseded files.** Markers like `outdated`, `deprecated`, `superseded`, `archived`, `do not use`, `replaced by`; version suffixes where a newer version exists; date references that predate newer copies. Route straight to Tier 3.
- **Conflicting files.** Two files cover the same topic with different content, or one references another as contradictory or replaced. Surface in the proposal step. Ask the user which is authoritative before placing either. Do not silently organize both into the same domain.
- **Domain clusters.** Groups of files about the same topic, even if scattered across folders.
- **Catch-all folders.** Folders with mixed unrelated content (e.g., `notes/` containing meeting notes, ideas, decisions, reference material). Not domains. Recommend dissolving and migrating each file individually.
- **Loose files.** Files that don't clearly belong to a cluster yet.
- **Hub-like files.** Any existing `*-index.md` files.

## Propose

Before presenting structure, ask: **"What are you currently working on?"** Use the answer to seed `status.md`.

Present findings with the recommended organization (memory tier, suggested domains, file moves, glossary content, ideas content, files staying put). Note the manifest is the routing file. Show the three CLAUDE.md lines that will be appended. Wait for confirmation. If the user adjusts groupings, incorporate changes.

## Build

Files have no dependencies on each other. Create concurrently where possible.

1. Move confirmed files to new locations. For each moved file, update `[[wikilinks]]` that referenced the old path.
2. Create domain hub files (`[domain]-index.md`). Each lists every file in the domain with `[[wikilink]]`, one-line summary, and status.
3. Create `_CLOSETS.md` in each domain folder. Format and rules: see [`memex/skills/session-end/references/closets-format.md`](../../session-end/references/closets-format.md). Per-entry summary fields follow the 8 rules in [`memex/skills/session-end/references/summary-rules.md`](../../session-end/references/summary-rules.md). Cap each closets file at ~30 entries. Older entries can be lazy-refreshed.
4. Create any missing Tier 1 files (`status.md`, `session-log.md`, `decisions.md`, `glossary.md`). Seed `status.md` with the user's answer. Also create `memory/_CLOSETS.md` from `memory-closets.md.tmpl` and populate one closets entry per Tier 1 file (status, session-log, decisions, glossary, plus any user-added Tier 1 files like contacts.md).
5. Seed `glossary.md` from glossary-like content found during the scan.
6. Create `scratch/ideas.md`. Migrate existing ideas content; move originals to Tier 3.
7. **Wikilink conversion (two passes):**
   - Pass 1 (automated): Run wikilinks script with `--suggest` for exact filename matches and hyphen-to-space matches. Apply without confirmation.
   - Pass 2 (proposed): Scan for semantic references (e.g., "the brand guidelines" → `brand-voice.md`). Present to user; apply only with confirmation.
8. Weave lateral cross-links across domains. Propose before applying.
9. Handle workspace-root `CLAUDE.md` (not `.claude/CLAUDE.md`):
   - Existing session hooks from another plugin → ask which plugin owns session lifecycle.
   - Other content → preserve it; append the three Memex lines.
   - No file → create with just the three Memex lines.
   - `.claude/CLAUDE.md` already has Memex session lines → skip root duplicate.
10. Create `_MANIFEST.md` mapping everything to tiers. Each file entry gets a one-line content summary. Hub Map entries get a domain summary. Write last.
11. Run wikilink verification. Must be CLEAN.
12. Output summary listing every file created, moved, wired, converted, cross-linked.
