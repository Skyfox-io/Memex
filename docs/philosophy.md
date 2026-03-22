# Why Structured Memory Matters

## The Problem Is Not Memory - It's Retrieval

AI agents can read files. They can write files. The raw capability for persistent memory exists. What doesn't exist is a system for deciding **what to load, when to load it, and how to keep it current.**

Without structure, you get one of two failure modes:

1. **Load everything.** Every file gets read at session start. Context fills up with stale information, rarely-referenced documents, and completed work. The agent runs out of room for actual task work.

2. **Load nothing.** The agent starts cold. You spend the first 10 minutes re-explaining context. Decisions from three sessions ago are forgotten. Work gets repeated.

Memex solves this with **tiered context loading** - a system that tells the agent exactly what to read, in what order, based on volatility and relevance.

## The Filing Cabinet Analogy

Claude Cowork Projects gives you a filing cabinet. Memex gives you the folders, labels, and the assistant who knows which drawer to open.

- **Tier 1** is the desk - always visible, always current
- **Tier 2** is the drawer - opened when you need that domain
- **Tier 3** is the archive - stored but never loaded unless asked

Without tiers, everything is in one pile on the desk. With tiers, the agent is as efficient on session 50 as it was on session 1.

## Why Markdown, Not a Database

Several memory systems use SQLite, vector stores, or MCP servers. Memex deliberately avoids all of these:

- **Transparency.** Every piece of memory is a readable, editable markdown file. You can open any file in any text editor and see exactly what Claude knows. Try that with a vector database.
- **No dependencies.** Memex requires nothing beyond a folder of files. No Python packages, no database engines, no running servers. It works anywhere Claude can read files.
- **Version control.** Markdown files work with git. Your memory has history, diffs, and blame. You can see exactly when a decision was recorded and what the status was on any given date.
- **Portability.** Move the folder, and the memory moves with it. No export/import, no migration scripts, no API keys.
- **[Obsidian](https://obsidian.md/) compatibility.** Markdown with `[[wikilinks]]` is exactly what Obsidian reads. Free visual knowledge graph with zero configuration.

## Why Automated Session Management

The most important design decision in Memex is that **the system maintains itself.** The user works; the skills handle the bookkeeping.

Session-start reads the right files and delivers a briefing. Session-end updates status, writes the handoff log, checks integrity. The user never has to remember to update a file or verify a link.

This matters because memory systems that require manual maintenance get abandoned. If updating your decision log feels like overhead, you stop doing it. If it happens automatically every time you say "wrap up," you never think about it.

## Why Wikilinks

Every cross-reference in Memex uses `[[wikilink]]` syntax instead of file paths. This provides:

- **Resilient navigation.** Wikilinks resolve by file stem, not full path. Move a file, and links still resolve.
- **[Obsidian](https://obsidian.md/) compatibility.** Every `[[link]]` becomes a clickable edge in the knowledge graph.
- **Integrity checking.** A simple script can verify that every link points to a real file. Broken links get caught at session end, not discovered three weeks later.
- **Human readability.** `[[decisions]]` is clearer than `[decisions](memory/decisions.md)` in running text.

## The Vannevar Bush Connection

The name is inspired by Vannevar Bush's 1945 essay ["As We May Think"](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/). Bush imagined a device that would store all of a person's books, records, and communications, with the ability to create "trails" of association between documents.

Eighty years later, that's what this is - a structured extension of working memory, with trails (wikilinks) connecting related documents, and a system (skills) that maintains it automatically. The tools changed; the need didn't.
