# Health Check Flow

> Referenced from the main init skill. Do not invoke this file directly.

When `_MANIFEST.md` exists with current version marker, delegate to the two dedicated health skills rather than reimplementing checks:

1. Run `/memex:lint` -- this covers Tier 1 file existence, Hub Map validity, status staleness, decision contradictions, orphan files, and stale blockers
2. Run `/memex:wikilinks` -- this covers broken link detection and missing wikilink conversion
3. Scan for untracked files and folders (content-aware -- read files, suggest domains). This is the one check that lint and wikilinks don't cover, because it requires content analysis to suggest domain groupings.

Combine the results into a single report:

```
Memex Health Check

Lint: [CLEAN or N warnings, M info]
Wikilinks: [CLEAN or N broken]
Untracked: [count files not in any hub or tier]

Overall: [HEALTHY or count issues found]
```

Offer to repair any issues found. For lint issues, offer `--fix`. For untracked files, suggest which domain they belong in.
