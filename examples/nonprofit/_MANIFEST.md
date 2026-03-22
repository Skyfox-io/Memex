# _MANIFEST.md - Bright Future Foundation Context Routing

> Read this file first in every session. It tells you what to load and when.

## Volatility Guide

| Marker | Meaning |
|--------|---------|
| `VOLATILE` | Updated frequently - re-read fresh every session. |
| `STABLE` | Rarely changes - safe to trust from prior context. |

## Tier 1 - Always Read

| File | Purpose | Freshness |
|------|---------|-----------|
| [[CLAUDE]] | Identity, voice, skill routing, session rules | STABLE |
| [[glossary]] | Term decoder for BFF-specific language | STABLE |
| [[status]] | Active work and blockers - prune-only snapshot | VOLATILE |
| [[session-log]] | Rolling handoff log - newest first, max 10 entries | VOLATILE |
| [[decisions]] | Key decisions as claims | STABLE |
| [[ideas]] | Raw idea inbox - reviewed at session start | VOLATILE |

## Tier 2 - Load by Domain

Read the hub file for a domain first. It links to everything in that domain.
Only go deeper into individual files if the task requires it.

### Programs
Hub: [[programs-index]] → After-school tutoring, STEAM Camp, college prep workshops

### Fundraising
Hub: [[fundraising-index]] → Grants, donor relations, spring campaign, events

## Tier 3 - Archival / Reference Only

Never load unless explicitly asked.

| File | Why archived | Date |
|------|-------------|------|
| [[session-log-archive]] | Older session log entries (auto-archived) | - |

## Archiving Rules

1. Move row from Tier 2 → Tier 3. Add the date.
2. Don't delete the file. Archiving just means Claude stops loading it.
3. If work is complete or superseded, archive it immediately.
4. At major milestones, review Tier 2 and suggest candidates for Tier 3. Ask before moving.
5. To unarchive: move the row back to the right domain section. Remove the date.

## Context Loading Rules

1. Always start with Tier 1.
2. Identify the domain. Load its hub file first.
3. Go deeper into individual files only if the task requires it.
4. Never load Tier 3 unless explicitly asked.
5. Any VOLATILE file must be re-read fresh - never trust prior session knowledge of it.
6. When referencing files in conversation, always use `[[filename]]` wikilink format.

## Hub Map

| Domain | Hub |
|--------|-----|
| Programs | [[programs-index]] |
| Fundraising | [[fundraising-index]] |
