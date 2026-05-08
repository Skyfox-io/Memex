#!/usr/bin/env python3
"""
Memex typed-edge extractor (deterministic, no LLM).

Parses YAML frontmatter from every markdown file in the workspace and writes
a graph index (memory/.graph.md by default) with typed edges between files.

Standard frontmatter keys recognized:
    type:           decision | person | project | meeting | reference | other
    people:         [[Alice]], [[Bob]]
    projects:       [[campaign-2026]]
    supersedes:     [[old-decision]]
    superseded-by:  [[newer-decision]]
    blocks:         [[other-task]]
    blocked-by:     [[upstream-task]]
    date:           YYYY-MM-DD
    status:         active | superseded | archived | draft

Frontmatter is OPTIONAL. Files without it still work; they just contribute
no typed edges. This script is purely additive.

Usage:
    python3 extract-graph.py /path/to/workspace [--output memory/.graph.md]
    python3 extract-graph.py /path/to/workspace --check
        Exit 1 if any typed edge points to a missing file.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
TYPED_KEYS = (
    "type",
    "people",
    "projects",
    "supersedes",
    "superseded-by",
    "blocks",
    "blocked-by",
    "date",
    "status",
)
LIST_KEYS = ("people", "projects", "supersedes", "superseded-by", "blocks", "blocked-by")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-ish frontmatter without depending on PyYAML.

    Supports the limited shape Memex needs: scalars, comma-separated wikilink
    lists. Returns (parsed_dict, remaining_content).
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    fm = content[3:end].strip()
    rest = content[end + 4:].lstrip("\n")
    parsed: dict = {}
    for line in fm.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        # strip surrounding quotes
        if val.startswith(("'", '"')) and val.endswith(("'", '"')):
            val = val[1:-1]
        if key in LIST_KEYS:
            # parse [[wikilinks]] from the value, ignore non-wikilink tokens
            parsed[key] = [m.group(1).strip() for m in WIKILINK_RE.finditer(val)]
        else:
            parsed[key] = val
    return parsed, rest


def collect_md_files(workspace: Path, skip_prefixes: list[str]) -> list[Path]:
    out = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.endswith(".md"):
                continue
            full = Path(root) / f
            rel = full.relative_to(workspace).as_posix()
            if any(rel.startswith(p) for p in skip_prefixes):
                continue
            out.append(full)
    return out


def build_graph(workspace: Path, files: list[Path]) -> dict:
    """Returns dict with: nodes (list), edges (list), counts, missing."""
    nodes = []
    edges = []
    by_stem: dict[str, str] = {}

    # First pass: collect known stems
    for f in files:
        stem = f.stem.lower()
        rel = f.relative_to(workspace).as_posix()
        by_stem[stem] = rel

    counts = defaultdict(int)
    by_type: dict[str, list[str]] = defaultdict(list)
    by_status: dict[str, list[str]] = defaultdict(list)
    missing: list[tuple[str, str, str]] = []  # (source, edge_type, target)

    EDGE_KEYS = ("people", "projects", "supersedes", "superseded-by", "blocks", "blocked-by")

    for f in files:
        rel = f.relative_to(workspace).as_posix()
        try:
            content = f.read_text()
        except Exception:
            continue
        fm, _ = parse_frontmatter(content)
        if not fm:
            continue

        node = {
            "stem": f.stem,
            "rel": rel,
            "type": fm.get("type", "other"),
            "status": fm.get("status", ""),
            "date": fm.get("date", ""),
        }
        nodes.append(node)
        if node["type"]:
            by_type[node["type"]].append(f.stem)
        if node["status"]:
            by_status[node["status"]].append(f.stem)

        for key in EDGE_KEYS:
            for target_stem in fm.get(key, []):
                tstem = target_stem.lower()
                edge = {"source": f.stem, "type": key, "target": target_stem}
                edges.append(edge)
                counts[key] += 1
                if tstem not in by_stem:
                    missing.append((f.stem, key, target_stem))

    return {
        "nodes": nodes,
        "edges": edges,
        "counts": dict(counts),
        "by_type": {k: sorted(v) for k, v in by_type.items()},
        "by_status": {k: sorted(v) for k, v in by_status.items()},
        "missing": missing,
        "total_files": len(files),
        "files_with_frontmatter": len(nodes),
    }


def render_graph_md(g: dict) -> str:
    out = []
    out.append("# Memex Typed-Edge Graph\n")
    out.append("<!-- auto-generated by extract-graph.py — do not edit by hand -->\n")
    out.append("> Auto-extracted from YAML frontmatter at session-end. Files without "
               "frontmatter contribute no edges and are not listed here.\n")
    out.append(f"\n**Stats:** {g['files_with_frontmatter']} files with frontmatter "
               f"out of {g['total_files']} markdown files. "
               f"{sum(g['counts'].values())} typed edges.\n")

    if g["counts"]:
        out.append("\n## Edge counts\n")
        out.append("| Edge type | Count |\n|---|---|\n")
        for k, v in sorted(g["counts"].items(), key=lambda x: -x[1]):
            out.append(f"| `{k}` | {v} |\n")

    if g["by_type"]:
        out.append("\n## Files by type\n")
        for t, stems in sorted(g["by_type"].items()):
            out.append(f"\n### {t}\n")
            out.append(", ".join(f"[[{s}]]" for s in stems) + "\n")

    if g["by_status"]:
        out.append("\n## Files by status\n")
        for s, stems in sorted(g["by_status"].items()):
            out.append(f"\n### {s}\n")
            out.append(", ".join(f"[[{x}]]" for x in stems) + "\n")

    # Per-node edge listing — useful for navigation
    if g["edges"]:
        out.append("\n## Typed edges\n")
        edges_by_source = defaultdict(list)
        for e in g["edges"]:
            edges_by_source[e["source"]].append(e)
        for src in sorted(edges_by_source):
            out.append(f"\n### [[{src}]]\n")
            for e in edges_by_source[src]:
                out.append(f"- `{e['type']}` → [[{e['target']}]]\n")

    if g["missing"]:
        out.append("\n## Dangling edges\n")
        out.append("These typed edges point to files that don't exist. "
                   "Either create the target files or remove the references.\n\n")
        for src, etype, tgt in g["missing"]:
            out.append(f"- [[{src}]] `{etype}` → [[{tgt}]] (missing)\n")

    return "".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", nargs="?", default=os.getcwd())
    parser.add_argument("--output", default="memory/.graph.md",
                        help="path relative to workspace; default memory/.graph.md")
    parser.add_argument("--skip", nargs="*",
                        default=[".claude", ".obsidian", ".git", "memex"],
                        help="path prefix(es) to skip")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any dangling edges; don't write file")
    parser.add_argument("--print", action="store_true",
                        help="print to stdout instead of writing file")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: {workspace} not a directory", file=sys.stderr)
        sys.exit(2)

    skip = [s.rstrip("/") + "/" for s in args.skip]
    files = collect_md_files(workspace, skip)
    g = build_graph(workspace, files)

    if args.check:
        if g["missing"]:
            print(f"DANGLING ({len(g['missing'])} found):")
            for src, etype, tgt in g["missing"]:
                print(f"  {src} {etype} -> {tgt}")
            sys.exit(1)
        print(f"CLEAN — {g['files_with_frontmatter']}/{g['total_files']} files "
              f"have frontmatter, {sum(g['counts'].values())} edges, no danglers")
        sys.exit(0)

    md = render_graph_md(g)
    if args.print:
        sys.stdout.write(md)
        return

    out_path = workspace / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    rel = out_path.relative_to(workspace)
    print(f"Wrote {rel} — {g['files_with_frontmatter']} nodes, "
          f"{sum(g['counts'].values())} edges, {len(g['missing'])} dangling")


if __name__ == "__main__":
    main()
