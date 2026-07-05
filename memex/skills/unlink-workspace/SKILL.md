---
name: unlink-workspace
description: >
  Removes a Memex workspace from the global source registry -- e.g. after a
  project is archived or moved -- so it stops appearing in `/memex:cross-search`.
  For a temporary opt-out instead, use `set-searchable false` (see Gotchas).
argument-hint: "[source-name]"
disable-model-invocation: true
---

# Memex - Unlink Workspace

**Wikilink rule:** When referencing any file in markdown, always use `[[filename]]` wikilink format.

Remove a workspace's entry from `~/.memex/sources.md`. The workspace files are not touched. Registry conventions and script-path resolution: `memex/skills/cross-search/references/registry.md`.

## Step 1: Source name

Use `$ARGUMENTS` if provided. Otherwise run `python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" list` and ask which to unlink.

## Step 2: Unlink

```
python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" remove <source-name>
```

If the name doesn't exist, surface the script's error.

## Step 3: Confirm

```
Unlinked: <source-name>

Workspace files untouched. To re-register: /memex:link-workspace.
```

## Gotchas

- **Unlink is destructive at the registry layer, not on disk.** The workspace's `_MANIFEST.md` and closets remain. Don't pitch unlink as a "delete".
- **Prefer `set-searchable false` for temporary hides.** Unlinking discards the registration date and forces a re-link to restore searchability. If the user just wants the source quiet for a while, point them to `python3 "${CLAUDE_SKILL_DIR}/scripts/sources.py" set-searchable <name> false`.
- **No undo.** The registry has no history. Re-linking creates a fresh `registered:` date.
- **Name is the only key.** If the user has multiple sources at similar paths, confirm by name before removing. The script does not prompt.
