# Migration Flow

> Referenced from the main init skill. Do not invoke this file directly.

When the version in the `<!-- memex-managed:X.X.X -->` marker is behind the current version:

1. List what changed between versions
2. Apply structural changes (e.g., add missing manifest sections)
3. Update the version in the marker
4. Run health check (see `references/health-check.md`)
5. Report what was migrated
