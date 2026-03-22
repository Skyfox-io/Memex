---
name: init
description: >
  Initialize, adopt, health-check, or upgrade a Memex workspace.
disable-model-invocation: true
---

# Memex - Init

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames. This is critical for [Obsidian](https://obsidian.md/) graph connectivity.

Set up Memex in a workspace. Behavior depends on what already exists.

**Core principle: never assume, never delete.** Existing files are sacred. Moves only happen with explicit confirmation.

---

## Step 1: Detect workspace state

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Check for five possible states:

| State | Detection | Action |
|-------|-----------|--------|
| **Empty workspace** | No markdown files, no manifest | Quick scaffold (see below) |
| **Has files, no manifest** | Markdown files exist, no `_MANIFEST.md` | Scan and organize (see below) |
| **Compatible manifest** | `_MANIFEST.md` exists, no `<!-- memex-managed` marker | Offer to add marker (opt-in to full Memex) or continue in compatible mode |
| **Old version** | `_MANIFEST.md` with `<!-- memex-managed:X.X.X -->` where version is behind current | Run migrations, update marker, then health check |
| **Current version** | `_MANIFEST.md` with current version marker | Run health check |

Do not tell the user which track or state was detected. Just run the appropriate flow.

---

## Quick Start (empty workspace)

For empty or near-empty workspaces. One question, then scaffold.

1. Ask: **"What are you working on right now?"** Use the answer to seed status.md with a real active focus, in-progress items, and next priorities.
2. Create `memory/status.md`, `memory/session-log.md`, `memory/decisions.md`, `memory/glossary.md` from templates. Fill status.md with the user's answer.
3. Create `scratch/ideas.md` from template.
4. Append Memex lines to the workspace-root `CLAUDE.md` (not `.claude/CLAUDE.md`, which is managed by the platform). If root `CLAUDE.md` exists, read it first, preserve existing content, and append the Memex lines at the end. If `.claude/CLAUDE.md` already contains Memex session lines, skip creating a root-level duplicate.
   ```
   > **FIRST ACTION EVERY SESSION:** Invoke `/memex:session-start` before doing anything else.
   > **LAST ACTION:** When the user signals they're done, invoke `/memex:session-end` automatically.
   > **ALWAYS:** When referencing any file in markdown you write or edit, use `[[filename]]` wikilink format.
   ```
5. Create `_MANIFEST.md` with marker, Tier 1 table pointing to created files, empty Tier 2, empty Tier 3, empty Hub Map. **Write this last** - it's the activation marker.
6. Output: "Memex is ready. Start a new session and the briefing will run automatically.

   **Visual layer:** Your workspace is now fully wikilinked. If you use [Obsidian](https://obsidian.md/), open this folder as a vault (File > Open Vault > Open folder as vault). You'll see a graph view (Cmd+G) showing how all your files connect. Every `[[wikilink]]` becomes a clickable edge in the graph. It's optional but recommended for navigating your knowledge base visually."

---

## Scan and Organize (existing files)

For workspaces with files. Scan, analyze, propose, then build with confirmation.

**Scan:**

```bash
find "$WORKSPACE_ROOT" -not -path "*/.git/*" -not -path "*/.claude/*" -not -path "*/.obsidian/*" | head -200
```

Read every markdown file to understand its content and purpose.

**Analyze:**

Based on file content (not just folder structure), identify:

- **Memory-like files** - status tracking, session logs, decision logs, glossaries
- **Glossary-like content** - acronym tables, people lists, shorthand definitions, terminology references. These get merged into glossary.md during the build phase.
- **Ideas-like files** - existing idea captures, brainstorm docs, inbox files. Content migrates to scratch/ideas.md; originals move to Tier 3.
- **Domain clusters** - groups of files about the same topic (e.g., 3 files about marketing, 4 about product). These become domain suggestions even if the files are scattered across folders.
- **Catch-all folders** - folders containing files that don't share a common topic (e.g., a `notes/` folder with meeting notes, ideas, decisions, and reference material mixed together). These are not domains. Flag them and recommend dissolving: migrate each file to the domain it actually belongs in, or to the appropriate memory file. Do not create a hub for a catch-all.
- **Loose files** - files that don't clearly belong to a cluster yet
- **Hub-like files** - any existing `*-index.md` files

**Propose structure:**

Before presenting the structure, ask: **"What are you currently working on?"** Use the answer to seed status.md.

Present findings and a recommended organization:

> "I found [count] markdown files. Here's what I'd suggest:
>
> **Tier 1 (memory - always loaded):**
> - [list memory-like files, or note which ones need creating]
>
> **Suggested domains (Tier 2):**
> - `marketing/` - [list files that belong here, with reasoning]
> - `product/` - [list files]
>
> **File moves to organize:**
> - `notes/campaign-plan.md` -> `marketing/campaign-plan.md`
> - `drafts/roadmap.md` -> `product/roadmap.md`
>
> **Glossary content found:** [list files with glossary-like content to merge]
>
> **Ideas content found:** [list existing ideas files to migrate]
>
> **Files staying where they are:** [list files that don't need to move]
>
> Everything gets wired through `_MANIFEST.md` at the root of your workspace. This is the routing file Claude reads at the start of every session to know what to load, what's in each domain, and what's archived. All the tiers, hubs, and files above route through it.
>
> I'll create hub files (`*-index.md`) for each domain and build the manifest. Want me to proceed? You can also adjust the groupings before I start."

Wait for confirmation. If the user adjusts groupings, incorporate changes.

**Build:**

These files have no dependencies on each other. Create them concurrently where possible to minimize tool calls:

1. Move confirmed files to their new locations. For each moved file, update any `[[wikilinks]]` that referenced the old path.
2. Create domain hub files (`[domain]-index.md`) for each domain. List every file in the domain with a `[[filename]]` wikilink, a one-line summary of the file's content, and status.
3. Create any missing Tier 1 files (status.md, session-log.md, decisions.md, glossary.md). Seed status.md with the user's answer about what they're working on.
4. **Seed glossary.md** from glossary-like content found during the scan (acronym tables, people lists, terminology). Merge relevant content into a single glossary file.
5. Create `scratch/ideas.md`. If an existing ideas-like file was found, migrate its content into scratch/ideas.md and move the original to Tier 3 (don't delete it).
6. **Convert existing files to wikilinks (two passes):**
   - **Pass 1 (automated):** Run the wikilinks script with `--suggest` to find exact filename matches (with or without `.md` extension) and hyphenated-to-space matches (e.g., "campaign plan" where `campaign-plan.md` exists). Apply these without confirmation.
   - **Pass 2 (proposed):** Scan file content for semantic references that clearly refer to a specific file by meaning rather than name (e.g., "the brand guidelines" where `brand-voice.md` exists). Present these to the user as a list of proposed conversions. Apply only with confirmation.
7. **Weave lateral cross-links.** Scan each file's content for references to concepts, people, or topics covered in files in other domains. Add `[[wikilinks]]` to create cross-domain connections. Examples: a campaign file that references brand guidelines should link to `[[brand-voice]]`. A press release about a product launch should link to the relevant campaign file. Present proposed lateral links to the user before applying.
8. Handle the workspace-root `CLAUDE.md` (not `.claude/CLAUDE.md`, which is managed by the platform):
   - **Root CLAUDE.md exists with session hooks from another plugin:** Note the conflict, ask which plugin should own session lifecycle.
   - **Root CLAUDE.md exists with other content:** Preserve all existing content. Append the three Memex lines at the end.
   - **No root CLAUDE.md:** Create one with just the three Memex lines.
   - **`.claude/CLAUDE.md` already contains Memex session lines:** Skip creating a root-level duplicate.
9. Create `_MANIFEST.md` mapping everything to tiers. For each file entry, include a one-line summary of the file's content (not just its purpose). For hub entries in the Hub Map, include a summary of what the domain covers. Write this last.
10. Run wikilink verification to confirm zero broken links.
11. Output summary listing every file created, moved, wired, converted, and cross-linked. End with:

   "Memex is ready. Start a new session and the briefing will run automatically.

   **Visual layer:** Your workspace is now fully wikilinked. If you use [Obsidian](https://obsidian.md/), open this folder as a vault (File > Open Vault > Open folder as vault). You'll see a graph view (Cmd+G) showing how all your files connect. Every `[[wikilink]]` becomes a clickable edge in the graph."

---

## Health Check (existing Memex workspace)

When `_MANIFEST.md` exists with current version marker:

1. Validate Tier 1 files exist on disk
2. Validate all Hub Map entries point to real files
3. Scan for untracked files and folders (content-aware - read files, suggest domains)
4. Run wikilink verification
5. Report results:

```
Memex Health Check

Tier 1 files: [count OK] / [count expected]
Hub files: [count OK] / [count expected]
Wikilinks: [CLEAN or count broken]
Untracked: [count files not in any hub or tier]

Overall: [HEALTHY or count issues found]
```

Offer to repair any issues found. For untracked files, suggest which domain they belong in.

---

## Migrations (old version marker)

When version is behind:
1. List what changed between versions
2. Apply structural changes (e.g., add missing manifest sections)
3. Update the version in the marker
4. Run health check
5. Report what was migrated

---

## Wikilink Rules

When creating or updating any file:
- Every file reference in a hub table must use `[[filename]]` wikilink format
- Every file reference in `_MANIFEST.md` must use `[[filename]]` wikilink format
- When moving a file, search all `.md` files for `[[old-name]]` and update to `[[new-name]]`
- After all writes, run wikilink verification to confirm zero broken links

---

## Rules

- **Never delete existing user files.** Moves require confirmation. Originals of migrated files go to Tier 3.
- **No placeholder text in saved files.**
- **Target workspace-root CLAUDE.md.** Not `.claude/CLAUDE.md`. Three Memex lines appended. Never modify existing content above them.
- **Manifest writes last.** It's the activation marker.
- **Always ask what the user is working on.** Seed status.md with a real answer.
- **Propose organization when files exist.** Suggest domain groupings and file moves based on content. User confirms before anything moves.
- **Glossary gets seeded.** Scan for glossary-like content and merge into glossary.md.
- **Ideas files get migrated.** Existing ideas content moves to scratch/ideas.md. Originals go to Tier 3.
- **Wikilink conversion in two passes.** Pass 1 (exact matches) is automated. Pass 2 (semantic references) is proposed to the user.
- **Lateral cross-links.** After building hubs, scan for cross-domain references and add wikilinks between files in different domains. Propose to user before applying.
- **Manifest summaries.** Every file entry gets a one-line content summary so session-start can scan without opening files.
- **Batch writes.** Memory files, hub files, and scratch can be created concurrently since they don't depend on each other.
