# Session Log Rotation

Read when `session-log.md` exceeds 10 entries after this session's prepend (Step 4).

Archive the oldest entries:

1. Read `session-log-archive.md` in full. If missing, create it with header `# Session Log - Archive`.
2. Prepend the oldest entries above existing archive content. Never overwrite existing entries.
3. If `[[session-log-archive]]` isn't in the Tier 3 table of `_MANIFEST.md`, add it:
   ```
   | [[session-log-archive]] | Older session log entries | YYYY-MM-DD |
   ```
