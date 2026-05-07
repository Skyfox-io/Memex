---
name: wikilinks
description: >
  Verify wikilink integrity (broken `[[targets]]`), then optionally suggest plain-text-to-wikilink
  conversions across the workspace. Explicit-invocation only; the conversion sweep is a workspace-wide
  bulk edit (auto-firing on a casual rename could propose hundreds of changes). Use when the
  user runs `/memex:wikilinks` directly, or says "verify wikilinks", "check for broken links",
  "convert plain text references to wikilinks", or "fix the Obsidian graph". For broader workspace
  audit (orphan files, stale status, manifest drift), use `/memex:lint` instead.
disable-model-invocation: true
---

# Memex - Wikilinks

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Two modes: **verify** broken links, then **suggest** plain-text → `[[wikilink]]` conversions.

## Step 1: Find workspace root

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

## Step 2: Verify wikilink integrity

Run `verify-wikilinks.py` (path resolution as in [session-end](../session-end/SKILL.md) Step 8a):

```bash
python3 [script-path] "$WORKSPACE_ROOT" --skip .claude .obsidian .git
```

If the script can't be found, report: "Wikilink script not found - skipping." Do not silently pass.

Report:

```
Broken links: 0
```

or:

```
BROKEN WIKILINKS ([count] found):
  [file]: [[broken-link]]
```

Offer fixes:
- Target renamed → update the link
- Target deleted → remove the link or replace with plain text
- Target never existed → flag for the user to decide

## Step 3: Suggest wikilink conversions

Re-run the script with `--suggest`:

```bash
python3 [script-path] "$WORKSPACE_ROOT" --suggest --skip .claude .obsidian .git
```

Scans markdown for plain-text mentions of existing filenames that aren't already `[[wrapped]]`. Handles exact and hyphenated-to-space matches. Skips code blocks, URLs, and frontmatter.

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

---

## Gotchas

- **Script missing → hard stop, not silent pass.** If neither resolution path finds `verify-wikilinks.py`, surface "Wikilink script not found - skipping." Reporting "0 broken" without a script run is a lie.
- **Short-filename false positives in `--suggest`.** Filenames ≤3 chars match common words (e.g., `api.md` matches every "API" in prose). Always review one-by-one before bulk-applying.
- **Inline code (single backticks) is not stripped.** Triple-fenced code blocks and URLs are excluded, but a backticked filename like "filename.md" in running prose can produce phantom suggestions.
- **Skip list is not exhaustive.** Default skips: `.claude/`, `.obsidian/`, `.git/`. Vendored deps, build outputs, or `node_modules/` need extra `--skip` flags or you'll get noise.
- **Verify ≠ orphan check.** This skill confirms `[[link]]` targets resolve. It does NOT detect files-on-disk-but-not-in-any-hub. That's `/memex:lint`.
