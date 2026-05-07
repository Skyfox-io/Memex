---
name: add-domain
description: >
  Add a new domain folder with a hub index and wire it into _MANIFEST.md. Use when
  the user says "add a domain", "create a marketing/product/research folder", or runs
  /memex:add-domain. Also use when scan suggests an obvious new cluster of files
  the user wants split out of an existing domain.
argument-hint: "[domain-name]"
disable-model-invocation: true
---

# Memex - Add Domain

**Wikilink rule:** Use `[[filename]]` for every file reference in markdown.

Create a domain folder with a hub index and a closets file, optionally migrate matching files into it, and wire it into `_MANIFEST.md`.

## Step 1: Validate workspace

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Read `_MANIFEST.md`. If missing: tell the user "No manifest found. Run `/memex:init` first." and stop.

## Step 2: Get the domain name

If `$ARGUMENTS` is set, use it. Otherwise ask. Convert to slug (lowercase, hyphens, no spaces).

## Step 3: Scan for files that belong in this domain

Scan the workspace for existing files about this topic (by content, not filename). If found, list them and ask whether to move them in. On confirmation, move and update `[[wikilinks]]` in other files that referenced the old paths.

## Step 4: Create the folder, hub, and closets file

Create `[domain-name]/` at the workspace root (or inside the established domains parent if existing Hub Map entries use one).

Create `[domain-name]/[domain-name]-index.md`:

```markdown
# [Domain Name]

[One sentence describing what this folder contains.]

---

| File | Purpose | Status |
|------|---------|--------|
```

Create `[domain-name]/_CLOSETS.md`. Format and per-entry typed-field schema (`subjects`, `people`, `claims`, `decisions`, `dates`, `status`) are canonical at [`memex/skills/session-end/references/closets-format.md`](../session-end/references/closets-format.md). Per-entry summary fields follow the 8 rules at [`memex/skills/session-end/references/summary-rules.md`](../session-end/references/summary-rules.md). Use `templates/closets.md.tmpl` from the init skill for the file header.

If files were moved in Step 3, list each in the hub table with `[[wikilink]]` + purpose + status, and add a closets entry per file populated from its content.

## Step 5: Update _MANIFEST.md

Add under **Tier 2 - By Domain**:

```markdown
### [Domain Name]
Hub: [[domain-name-index]]
```

Add a row to the **Hub Map** with a one-line summary:

```markdown
| [Domain Name] | [[domain-name-index]] | [one-line summary] |
```

## Step 6: Verify wikilinks

Run wikilink verification. Fix any breaks before finishing.

## Step 7: Confirm

```
Domain added: [domain-name]
  Hub:      [domain-name]/[domain-name]-index.md
  Closets:  [domain-name]/_CLOSETS.md
  Files moved: [count or "none"]
  Manifest: updated
  Wikilinks: CLEAN
```

---

## Gotchas

- **No manifest = no domain.** If `_MANIFEST.md` is missing, stop and route the user to `/memex:init`. Don't scaffold a half-wired domain.
- **Slugify the input.** "Marketing Strategy" → `marketing-strategy`. Spaces and uppercase break wikilinks and file resolution downstream.
- **Don't duplicate an existing domain.** Before creating, scan the Hub Map for similar slugs (`marketing` vs `marketing-strategy` vs `mkt`). Ask the user whether to merge into the existing domain instead of forking.
- **Domain root location follows existing convention.** If existing Hub Map entries put domains under `domains/<name>/` or `areas/<name>/`, mirror that. Don't drop a new domain at workspace root if siblings live in a parent folder.
- **Moved files keep their wikilinks alive.** Every move triggers a `[[old-name]]` → `[[new-name]]` rewrite across all `.md` files. Skipping this leaves the Obsidian graph broken even though tests pass.
- **Closets entry per moved file is required.** Hub table without a matching `_CLOSETS.md` entry breaks the two-tier retrieval contract. Populate from file content, not filename.
- **Catch-all topics aren't domains.** "miscellaneous", "other", "stuff" — refuse politely and ask the user to name a real subject area.
