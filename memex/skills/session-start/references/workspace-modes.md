# Workspace Mode Handling

Read this when Step 1 finds anything other than "no manifest" or "marker present and current version": an outdated `<!-- memex-managed:N.N.N -->` marker, or no marker at all (compatible mode).

## Outdated marker

Parse the version from `<!-- memex-managed:N.N.N -->`. If the major version is older than the current Memex VERSION (read `memex/.claude-plugin/plugin.json` if accessible; the v2 baseline is `2.0.0`), this is an outdated workspace.

Continue normally, but in Step 6 append a one-line notice:

```
Memex upgrade available. Run /memex:upgrade to migrate to v2 retrieval.
```

If the marker's major version actually matches current, treat it as full Memex mode and proceed (this path only fires when Step 1's fast check was skipped).

## No marker, but Tier 1/2/3 structure present (compatible mode)

Continue as normal. After Step 6's briefing, append:

```
Running in compatible mode. Run /memex:init to enable full features, then /memex:upgrade to migrate to v2 retrieval.
```
