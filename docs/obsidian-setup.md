# Obsidian Integration

Obsidian is optional but recommended. It turns your Memex workspace into a live visual knowledge graph where every `[[wikilink]]` becomes a navigable connection.

## Setup

1. Open Obsidian
2. Click **Open folder as vault** (home screen, or File → Open Vault)
3. Navigate to your Memex workspace directory and select it
4. Obsidian indexes all `.md` files automatically - no configuration needed

Every `[[wikilink]]` in the files immediately becomes a live, clickable edge in the graph.

> If Obsidian asks about trusting the vault, say yes. If it offers to create a `.obsidian` config folder inside your directory, allow it - this stores your graph settings and theme preferences. It doesn't affect how Claude reads the files, and the wikilink scan skips it automatically.

## Graph View

Press **Cmd+G** (Mac) or **Ctrl+G** (Windows). Every `.md` file appears as a node; every `[[link]]` appears as an edge.

What you'll see:

- **`_MANIFEST.md`** - the most-connected node; it links to every domain hub
- **Hub index files** - mid-size nodes at the center of each domain cluster
- **`memory/` files** - dense cluster, all cross-linked
- **`working/scratch/ideas.md`** - connected to memory cluster via session-start reads
- **Tier 3 archived files** - sparse, isolated at the edges (this is correct - they're not linked from active files)
- **Ghost files** - if Obsidian auto-created any 0-byte `.md` stubs by clicking an unresolved link, they'll appear as orphaned nodes. Delete them (right-click → Move to Trash) or in Finder.

## Color Groups

In Graph View, click the **gear icon** (top-left of the panel) → **Groups**. Add one group per folder. First match wins, so order matters - put more specific paths before broader ones.

Example groups:

| Group name | Filter | Suggested color |
|------------|--------|-----------------|
| Memory | `path:memory/` | Gold / amber |
| Scratch | `path:working/scratch/` | Gray |
| [Domain 1] | `path:working/[domain-1]/` | Blue |
| [Domain 2] | `path:working/[domain-2]/` | Purple |
| [Domain 3] | `path:working/[domain-3]/` | Teal |
| [Domain 4] | `path:working/[domain-4]/` | Green |
| Root | `path:` | White |

Color choice is personal preference. The goal is that each domain reads as a visually distinct cluster at a glance.

## Navigation Shortcuts

| Action | Shortcut |
|--------|----------|
| Open any file by name | Cmd+O |
| Full-text search | Cmd+Shift+F |
| Toggle graph view | Cmd+G |
| See what links to current file | Right panel → Backlinks |
| See all outgoing links | Right panel → Outgoing links |
| Follow a wikilink | Cmd+click |

## Keeping Obsidian and Claude in Sync

- **Rename files in Finder or via Claude, not inside Obsidian.** Obsidian will try to update links it knows about, but Claude won't know the rename happened until the next wikilink scan. Use the session-end skill to catch drift.
- **Don't click unresolved links in Obsidian.** Clicking a dotted (unresolved) link creates a blank stub file. This pollutes the workspace with empty files. If you see dotted links, run `/memex:wikilinks` to find the source and fix it.
- **No pipe aliases in table cells.** `[[name|display text]]` inside a Markdown table breaks table rendering. Pipe aliases are fine in regular prose.
- **The `.obsidian/` folder is safe to ignore.** Claude's wikilink scan skips all hidden folders. Don't delete `.obsidian/` - it stores your graph groups, theme, and settings.
