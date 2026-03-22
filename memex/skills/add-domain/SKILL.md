---
name: add-domain
description: >
  Add a new domain folder with a hub index and wire it into the manifest.
argument-hint: "[domain-name]"
disable-model-invocation: true
---

# Memex - Add Domain

**Wikilink rule:** When referencing any file in any markdown content you write or edit, always use `[[filename]]` wikilink format. Never use plain text filenames.

Create a domain folder with a hub index file and wire it into `_MANIFEST.md`.

## Step 1: Validate workspace

Run `WORKSPACE_ROOT=$(pwd) && echo "$WORKSPACE_ROOT"` via Bash.

Read `_MANIFEST.md`. If it does not exist, tell the user: "No manifest found. Run `/memex:init` first." and stop.

## Step 2: Get the domain name

If the user provided a domain name via `$ARGUMENTS`, use it. Otherwise, ask for one. Convert to a slug (lowercase, hyphens, no spaces).

## Step 3: Scan for files that belong in this domain

Before creating the folder, scan the workspace for existing files that appear to be about this domain topic (based on content, not just filename). If found, list them:

> "These existing files look like they belong in [domain-name]/:
> - `notes/campaign-plan.md` (marketing strategy document)
> - `drafts/social-media-calendar.md` (content planning)
>
> Want me to move them into the new domain folder?"

If the user confirms, move the files. Update any `[[wikilinks]]` in other files that reference the moved files.

## Step 4: Create the folder and hub

Create `[domain-name]/` at the workspace root (or inside the domains parent if one is established by existing domains in the Hub Map).

Create `[domain-name]/[domain-name]-index.md`:

```markdown
# [Domain Name]

[One sentence describing what this folder contains.]

---

| File | Purpose | Status |
|------|---------|--------|
```

If files were moved into this domain in Step 3, list each one in the hub table with a `[[filename]]` wikilink, its purpose, and status.

## Step 5: Update _MANIFEST.md

Add a section under **Tier 2 - By Domain**:

```markdown
### [Domain Name]
Hub: [[domain-name-index]]
```

Add a row to the **Hub Map** with a one-line summary of what the domain covers:

```markdown
| [Domain Name] | [[domain-name-index]] | [one-line summary of domain content] |
```

## Step 6: Verify wikilinks

Run the wikilink verification script to confirm zero broken links after any file moves and the new hub creation. Fix any breaks before finishing.

## Step 7: Confirm

```
Domain added: [domain-name]
  Hub: [domain-name]/[domain-name]-index.md
  Files moved: [count or "none"]
  Manifest: updated
  Wikilinks: CLEAN
```
