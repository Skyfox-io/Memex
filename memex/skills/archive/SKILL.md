---
name: archive
description: >
  Move a file from active (Tier 2) to archived (Tier 3) when it's no longer needed for current
  work. Use when a project wraps up, a reference goes stale, or a file is superseded.
argument-hint: "[filename]"
disable-model-invocation: true
---

# Memex - Archive

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Move a file from active use (Tier 2) to archival (Tier 3) in the manifest. The file stays on disk. Archiving just means Claude stops loading it automatically.

## Step 1: Find workspace root

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Read `_MANIFEST.md`. If it does not exist, tell the user: "No manifest found. Run `/memex:init` first." and stop.

## Step 2: Identify the file

If the user provided a filename via `$ARGUMENTS`, use it. Otherwise, read the Tier 2 sections from `_MANIFEST.md` and show the entries. Ask which one to archive.

## Step 3: Move in manifest

1. Remove the file's row from its Tier 2 domain section
2. Add the file to the **Tier 3** table with today's date and a brief reason

```markdown
| [filename] | [why archived] | YYYY-MM-DD |
```

## Step 4: Update the hub

Read the relevant domain hub file. Update the file's status to "Archived" or remove it from the active table.

## Step 5: Confirm

```
Archived: [filename]
  From: Tier 2 ([domain name])
  Reason: [why]
  Date: YYYY-MM-DD

To unarchive: move the row back to Tier 2 in _MANIFEST.md.
```
