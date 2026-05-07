#!/usr/bin/env python3
"""
Memex cross-workspace source registry.

Sources are independent Memex workspaces registered globally so the user can
search across them. The registry lives at ~/.memex/sources.md (file-based,
human-readable, no DB). Each source has a name, an absolute path, and a
flag indicating whether it is `cross-source-searchable`.

Search is grep-based across each source's `_MANIFEST.md`, `_CLOSETS.md`,
and `_CLOSETS-archive.md` files. Results are grouped by source.

Subcommands:
    list                List all registered sources
    add NAME PATH       Register a workspace as a source
    remove NAME         Deregister a source
    set-searchable NAME true|false  Toggle cross-source-searchable flag
    search QUERY        Grep across registered sources' manifests + closets
    search-local QUERY  Grep within the current workspace, grouped by folder
    where               Show registry path

Privacy: sources opt in via `cross-source-searchable: true`. Sources marked
`false` are still listed but never searched.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REGISTRY_DIR = Path.home() / ".memex"
REGISTRY_FILE = REGISTRY_DIR / "sources.md"

REGISTRY_TEMPLATE = """# Memex Sources

> Cross-workspace registry. Each source is an independent Memex workspace.
> Sources marked `searchable: true` are included in `/memex:cross-search`.

<!-- memex-sources-version:1 -->

"""


def ensure_registry() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.write_text(REGISTRY_TEMPLATE)


def parse_registry() -> list[dict]:
    """Parse sources.md into list of source dicts."""
    if not REGISTRY_FILE.exists():
        return []
    text = REGISTRY_FILE.read_text()
    sources: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(\S+)\s*$", line)
        if m:
            if current:
                sources.append(current)
            current = {"name": m.group(1), "path": "", "registered": "", "searchable": True}
            continue
        if current is None:
            continue
        m = re.match(r"^-\s+(\w+)\s*:\s*(.+)$", line.strip())
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key in ("path", "registered", "searchable"):
            if key == "searchable":
                current[key] = val.lower() in ("true", "yes", "1")
            else:
                current[key] = val
    if current:
        sources.append(current)
    return sources


def write_registry(sources: list[dict]) -> None:
    ensure_registry()
    out = [REGISTRY_TEMPLATE.rstrip(), ""]
    for s in sources:
        out.append(f"## {s['name']}")
        out.append(f"- path: {s['path']}")
        out.append(f"- registered: {s['registered']}")
        out.append(f"- searchable: {'true' if s.get('searchable', True) else 'false'}")
        out.append("")
    REGISTRY_FILE.write_text("\n".join(out) + "\n")


# --- Subcommands -----------------------------------------------------------

def cmd_list(args):
    sources = parse_registry()
    if not sources:
        print(f"No sources registered. Use `sources.py add NAME PATH` to register one.")
        print(f"Registry: {REGISTRY_FILE}")
        return
    for s in sources:
        flag = "✓" if s.get("searchable", True) else "✗"
        print(f"  {flag} {s['name']:24s} {s['path']}  (registered {s['registered']})")


def cmd_add(args):
    path = Path(args.path).resolve()
    if not path.is_dir():
        print(f"ERROR: {path} is not a directory", file=sys.stderr)
        sys.exit(2)
    if not (path / "_MANIFEST.md").exists():
        print(f"WARNING: {path}/_MANIFEST.md not found — is this a Memex workspace?", file=sys.stderr)
    sources = parse_registry()
    if any(s["name"] == args.name for s in sources):
        print(f"ERROR: source name '{args.name}' already registered", file=sys.stderr)
        sys.exit(2)
    sources.append({
        "name": args.name,
        "path": str(path),
        "registered": datetime.now().date().isoformat(),
        "searchable": True,
    })
    write_registry(sources)
    print(f"Registered '{args.name}' → {path}")


def cmd_remove(args):
    sources = parse_registry()
    before = len(sources)
    sources = [s for s in sources if s["name"] != args.name]
    if len(sources) == before:
        print(f"ERROR: no source named '{args.name}'", file=sys.stderr)
        sys.exit(2)
    write_registry(sources)
    print(f"Removed source '{args.name}'")


def cmd_set_searchable(args):
    val = args.value.lower() in ("true", "yes", "1")
    sources = parse_registry()
    found = False
    for s in sources:
        if s["name"] == args.name:
            s["searchable"] = val
            found = True
    if not found:
        print(f"ERROR: no source named '{args.name}'", file=sys.stderr)
        sys.exit(2)
    write_registry(sources)
    print(f"Source '{args.name}' searchable={val}")


def _search_workspace(path: Path, query: str) -> list[str]:
    """Grep `_MANIFEST.md` + every `_CLOSETS.md`/`_CLOSETS-archive.md` under
    `path`. Returns grep_lines.
    """
    targets = [
        path / "_MANIFEST.md",
        *path.rglob("_CLOSETS.md"),
        *path.rglob("_CLOSETS-archive.md"),
    ]
    targets = [t for t in targets if t.exists()]
    grep_lines: list[str] = []
    if targets:
        cmd = ["grep", "-Hn", "-i", query] + [str(t) for t in targets]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            grep_lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
        except subprocess.TimeoutExpired:
            grep_lines = ["(grep timeout)"]
    return grep_lines


def cmd_search(args):
    sources = parse_registry()
    searchable = [s for s in sources if s.get("searchable", True)]
    if not searchable:
        print("No searchable sources registered.")
        return

    query = args.query
    print(f"Searching {len(searchable)} source(s) for: {query}\n")

    total_hits = 0
    for s in searchable:
        path = Path(s["path"])
        if not path.is_dir():
            print(f"  [{s['name']}] (path missing: {path})\n")
            continue
        grep_lines = _search_workspace(path, query)
        if not grep_lines:
            continue
        print(f"=== {s['name']} ({s['path']}) ===")
        for ln in grep_lines[:20]:
            print(f"  {ln}")
        if len(grep_lines) > 20:
            print(f"  ... and {len(grep_lines)-20} more grep matches")
        print()
        total_hits += len(grep_lines)

    print(f"Total hits: {total_hits} grep across {len(searchable)} sources")


def cmd_search_local(args):
    """Within-workspace search: grep `_MANIFEST.md` + every `_CLOSETS.md` /
    `_CLOSETS-archive.md` under the current workspace. Output groups results
    by folder for cross-hub queries within a single workspace.
    """
    path = Path(args.workspace).resolve() if hasattr(args, "workspace") and args.workspace else Path.cwd()
    if not path.is_dir():
        print(f"ERROR: {path} is not a directory", file=sys.stderr)
        sys.exit(2)
    if not (path / "_MANIFEST.md").exists():
        print("ERROR: no _MANIFEST.md in current workspace. Run /memex:init first.", file=sys.stderr)
        sys.exit(2)

    query = args.query
    print(f"Searching workspace for: {query}\n")

    grep_lines = _search_workspace(path, query)

    if not grep_lines:
        print(f"No matches for \"{query}\" in {path}.")
        return

    by_folder: dict[str, list[str]] = {}
    for ln in grep_lines:
        try:
            file_part = ln.split(":", 1)[0]
            rel = str(Path(file_part).resolve().relative_to(path))
        except ValueError:
            rel = ln.split(":", 1)[0]
        folder = str(Path(rel).parent) if "/" in rel else "."
        by_folder.setdefault(folder, []).append(ln)

    for folder in sorted(by_folder):
        print(f"=== {folder} ===")
        for ln in by_folder[folder][:20]:
            print(f"  {ln}")
        if len(by_folder[folder]) > 20:
            print(f"  ... and {len(by_folder[folder])-20} more grep matches")
        print()

    print(f"Total hits: {len(grep_lines)} grep across {len(by_folder)} folders")


def cmd_where(args):
    print(REGISTRY_FILE)


# --- main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="sources.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    p = sub.add_parser("add")
    p.add_argument("name")
    p.add_argument("path")

    p = sub.add_parser("remove")
    p.add_argument("name")

    p = sub.add_parser("set-searchable")
    p.add_argument("name")
    p.add_argument("value", choices=["true", "false", "yes", "no", "1", "0"])

    p = sub.add_parser("search")
    p.add_argument("query")

    p = sub.add_parser("search-local")
    p.add_argument("query")
    p.add_argument("--workspace", default=os.getcwd(),
                   help="workspace path (default: current directory)")

    sub.add_parser("where")

    args = parser.parse_args()
    cmd_map = {
        "list": cmd_list, "add": cmd_add, "remove": cmd_remove,
        "set-searchable": cmd_set_searchable, "search": cmd_search,
        "search-local": cmd_search_local, "where": cmd_where,
    }
    cmd_map[args.cmd](args)


if __name__ == "__main__":
    main()
