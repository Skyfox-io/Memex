---
name: archive
description: >
  Move a file from active (Tier 2) to archived (Tier 3) so Memex stops loading it
  automatically. Use when a project wraps, a reference goes stale, a file is
  superseded by a newer version, or the user says "archive X", "retire X",
  "stop loading X", or runs /memex:archive. The file stays on disk; only its
  manifest tier and hub status change.
argument-hint: "[filename]"
disable-model-invocation: true
---

# Memex - Archive

**Wikilink rule:** Use `[[filename]]` for every file reference in markdown.

Move a file from Tier 2 to Tier 3 in `_MANIFEST.md` and update its hub status. The file stays on disk; archiving just stops auto-loading.

## Step 1: Find workspace root

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Read `_MANIFEST.md`. If missing: tell the user "No manifest found. Run `/memex:init` first." and stop.

## Step 2: Identify the file

If `$ARGUMENTS` is set, use it. Otherwise read the Tier 2 sections from `_MANIFEST.md`, show the entries, and ask which to archive.

## Step 3: Move in manifest

1. Remove the file's row from its Tier 2 domain section.
2. Add to the **Tier 3** table with today's date and a brief reason:

```markdown
| [[filename]] | [why archived] | YYYY-MM-DD |
```

## Step 4: Update the hub and closets

Read the relevant domain hub. Set the file's status to `Archived`, or remove it from the active table.

Then update the file's entry in `<domain>/_CLOSETS.md` (or `_CLOSETS-archive.md` if it lives there per pagination). Change the entry's `status:` line to `status: archived`. If the file has no closets entry yet, skip. Session-end will not re-create it for an archived file.

Closets schema and field semantics: [`memex/skills/session-end/references/closets-format.md`](../session-end/references/closets-format.md).

## Step 5: Confirm

```
Archived: [filename]
  From:   Tier 2 ([domain name])
  Reason: [why]
  Date:   YYYY-MM-DD

To unarchive: move the row back to Tier 2 in _MANIFEST.md.
```

---

## Gotchas

- **Archive is a manifest move, not a file deletion.** The file stays on disk. Don't `rm` it. Don't move it to an `archive/` folder unless the user explicitly asks. That breaks existing wikilinks.
- **Tier 3 entries still need wikilinks.** Use `[[filename]]` in the Tier 3 row so the Obsidian graph keeps the node connected.
- **Don't strip the closets entry.** The file's `_CLOSETS.md` entry stays, with `status: archived`. Future searches still surface it, just at lower priority.
- **Tier 1 files don't archive.** `status.md`, `decisions.md`, `glossary.md`, etc. are always-loaded by design. Refuse and explain.
- **Reason is load-bearing.** Examples: "wrapped", "superseded by `[[new-file]]`", "stale". Future you reads this when deciding whether to unarchive. "no longer needed" is not a reason.
