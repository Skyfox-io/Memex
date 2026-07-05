---
name: link-workspace
description: >
  Registers this Memex workspace in the global source registry so it's searchable
  from your other workspaces via `/memex:cross-search`.
argument-hint: "[source-name]"
disable-model-invocation: true
---

# Memex - Link Workspace

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Register the current workspace in `~/.memex/sources.md`. Registry conventions, script-path resolution, and privacy semantics live in `memex/skills/cross-search/references/registry.md`. CLI surface: `${CLAUDE_SKILL_DIR}/scripts/sources.py`.

## Step 0: Validate workspace

`WORKSPACE_ROOT=$(pwd)`. Read `_MANIFEST.md`. If absent, tell the user "No manifest found. Run `/memex:init` first." and stop.

## Step 1: Source name

Use `$ARGUMENTS` if provided. Otherwise propose a slug-ified default from the workspace folder name and ask to confirm. Names should be short, slug-style, and meaningful across workspaces (e.g., `nonprofit-foundation`, `personal`, `dashflow`).

## Step 2: Register

```
python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" add <source-name> <WORKSPACE_ROOT>
```

If the script reports the name is taken: tell the user "A source named '<name>' is already registered (run `python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" list` to see all). Pick a different name or `/memex:unlink-workspace <name>` first."

## Step 3: Confirm

```
Linked: <source-name> → <WORKSPACE_ROOT>
Searchable: yes (default)

Searchable from other workspaces via:
  /memex:cross-search <query>

Opt out:
  python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" set-searchable <source-name> false
```

## Gotchas

- **Path is captured at link time, absolute.** If the workspace later moves, the registry entry breaks silently. Cross-search will report "path missing". Re-link after moves.
- **Not idempotent.** Re-running with the same name errors out instead of updating. To change the path, unlink then re-link.
- **`_MANIFEST.md` missing only warns, doesn't block** at the script layer. This skill validates first so the user gets a clearer message. Don't skip Step 0.
- **Symlinked workspace roots** are resolved to their real path by the script. If you link via a symlink, the registry shows the resolved target.
