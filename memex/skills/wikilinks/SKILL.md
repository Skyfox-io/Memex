---
name: wikilinks
description: >
  Check wikilink integrity and convert plain text file references to [[wikilinks]].
---

# Memex - Wikilinks

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Two modes: **check** for broken links, and **convert** to find plain text references that should be wikilinks.

## Step 1: Find workspace root

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

## Step 2: Check for broken wikilinks

Resolve the verification script path:

1. `${CLAUDE_PLUGIN_ROOT}/scripts/verify-wikilinks.py` (if set)
2. `${CLAUDE_SKILL_DIR}/../scripts/verify-wikilinks.py` (fallback)

Run with skip flags:

```bash
python3 [script-path] "$WORKSPACE_ROOT" --skip .claude .obsidian .git
```

If the script can't be found, report: "Wikilink script not found - skipping." Do not silently pass.

Report results:

If clean:
```
Broken links: 0
```

If broken:
```
BROKEN WIKILINKS ([count] found):
  [file]: [[broken-link]]
```

Offer to fix broken links:
- If target was renamed, update the link
- If target was deleted, remove the link or replace with plain text
- If target never existed, flag it for the user to decide

## Step 3: Scan for missing wikilinks

Run the same script with `--suggest` to find plain text references that should be wikilinks:

```bash
python3 [script-path] "$WORKSPACE_ROOT" --suggest --skip .claude .obsidian .git
```

The script scans all markdown files for plain text mentions of filenames that exist in the workspace but aren't inside `[[wikilinks]]`. It handles exact matches, hyphenated-to-space matches, and skips code blocks, URLs, and frontmatter.

## Step 4: Present conversion suggestions

```
WIKILINK CONVERSIONS ([count] suggested):

  marketing-plan.md:
    Line 12: "see the budget spreadsheet" -> "see the [[budget]] spreadsheet"
    Line 34: "based on the roadmap" -> "based on the [[roadmap]]"

  meeting-notes.md:
    Line 5: "discussed pitch deck" -> "discussed [[pitch-deck]]"

Apply all [count] conversions? (or review one by one)
```

If the user confirms, apply the conversions. If they want to review, go through each one and ask.

## Step 5: Report summary

```
Wikilinks report:

Broken links: [count fixed or 0]
Conversions applied: [count]
Total wikilinks in workspace: [count]
Files scanned: [count]

Obsidian graph: [count] nodes, [count] edges
```
