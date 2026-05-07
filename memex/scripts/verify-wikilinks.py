#!/usr/bin/env python3
"""
Memex wikilink checker and converter.

Modes:
    python3 verify-wikilinks.py /path/to/workspace [--skip prefix1 prefix2 ...]
        Check for broken [[wikilinks]]. Exit 1 if broken links found.

    python3 verify-wikilinks.py /path/to/workspace --suggest [--skip prefix1 prefix2 ...]
        Find plain text references to files that should be [[wikilinks]].
        Outputs suggestions in a parseable format. Exit 0 always.

If no path is provided, uses the current working directory.
The --skip flag accepts directory prefixes to exclude.
Default skips: .claude/, .obsidian/, .git/
"""

import os
import re
import sys


def collect_files(workspace):
    """Walk workspace, skipping hidden directories."""
    all_files = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, workspace)
            all_files.append(rel)
    return all_files


def build_known_names(all_files):
    """Build sets of known file stems and paths for resolution."""
    known_stems = set()
    known_paths = set()
    stem_to_file = {}
    for rel in all_files:
        stem = os.path.splitext(os.path.basename(rel))[0]
        known_stems.add(stem.lower())
        known_paths.add(rel.lower())
        known_paths.add(os.path.splitext(rel)[0].lower())
        stem_to_file[stem.lower()] = rel
    return known_stems, known_paths, stem_to_file


def strip_code_blocks(content):
    """Remove code blocks so we don't check links inside them."""
    # Order matters: strip fenced blocks (longest delimiter first) before inline
    content = re.sub(r"````[\s\S]*?````", "", content)
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"`[^`]+`", "", content)
    return content


def strip_frontmatter(content):
    """Remove YAML frontmatter."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:]
    return content


def _is_closets_file(rel):
    """A closets file is _CLOSETS.md or its overflow sibling _CLOSETS-archive.md."""
    base = os.path.basename(rel)
    return base == "_CLOSETS.md" or base == "_CLOSETS-archive.md"


def find_broken_links(workspace, all_files, known_stems, known_paths, skip_prefixes):
    """Find all broken wikilinks in markdown files."""
    broken = []

    for rel in all_files:
        if not rel.endswith(".md"):
            continue
        if any(rel.startswith(p) for p in skip_prefixes):
            continue
        # Closets files are validated by find_closets_issues; skip here
        # to avoid duplicate reporting of the same dangling reference.
        if _is_closets_file(rel):
            continue

        full = os.path.join(workspace, rel)
        try:
            with open(full) as f:
                content = f.read()
        except Exception:
            continue

        content_stripped = strip_code_blocks(content)
        links = re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]", content_stripped)

        for link in links:
            link = link.strip()
            link_lower = link.lower()

            if "/" in link:
                stem = os.path.splitext(os.path.basename(link))[0].lower()
                if (
                    stem in known_stems
                    or link_lower in known_paths
                    or (link_lower + ".md") in known_paths
                ):
                    continue
                broken.append((rel, link))
            else:
                stem = os.path.splitext(link)[0].lower()
                if stem in known_stems:
                    continue
                broken.append((rel, link))

    return broken


def find_missing_wikilinks(workspace, all_files, known_stems, stem_to_file, skip_prefixes):
    """Find plain text references to files that should be [[wikilinks]]."""
    suggestions = []

    # Only suggest for stems with 3+ characters to avoid false positives
    candidate_stems = {s for s in known_stems if len(s) >= 3}

    # Build patterns: match stem as a whole word, not inside [[]] or URLs
    # Also match hyphenated names as space-separated words
    stem_patterns = {}
    for stem in candidate_stems:
        # Match the stem as-is (whole word)
        patterns = [stem]
        # Also match with hyphens replaced by spaces (e.g., "campaign plan" for "campaign-plan")
        if "-" in stem:
            patterns.append(stem.replace("-", " "))
        stem_patterns[stem] = patterns

    for rel in all_files:
        if not rel.endswith(".md"):
            continue
        if any(rel.startswith(p) for p in skip_prefixes):
            continue

        full = os.path.join(workspace, rel)
        try:
            with open(full) as f:
                content = f.read()
        except Exception:
            continue

        # Don't suggest converting references in the file to itself
        own_stem = os.path.splitext(os.path.basename(rel))[0].lower()

        content_clean = strip_frontmatter(content)
        content_clean = strip_code_blocks(content_clean)

        lines = content_clean.split("\n")
        for line_num, line in enumerate(lines, 1):
            # Skip lines that are inside wikilinks, URLs, or HTML comments
            if "http://" in line or "https://" in line:
                # Remove URLs before checking
                line_check = re.sub(r"https?://\S+", "", line)
            else:
                line_check = line

            # Remove existing wikilinks from the check line
            line_check = re.sub(r"\[\[[^\]]+\]\]", "", line_check)

            # Skip HTML comments
            line_check = re.sub(r"<!--.*?-->", "", line_check)

            line_lower = line_check.lower()

            for stem, patterns in stem_patterns.items():
                if stem == own_stem:
                    continue
                for pattern in patterns:
                    # Word boundary match
                    match = re.search(r"\b" + re.escape(pattern) + r"\b", line_lower)
                    if match:
                        # Get the actual text from the original line at that position
                        start = match.start()
                        end = match.end()
                        original_text = line_check[start:end]
                        target_file = stem_to_file.get(stem, stem)
                        suggestions.append((rel, line_num, original_text, stem))
                        break  # One suggestion per stem per line

    return suggestions


def main():
    args = sys.argv[1:]
    workspace = os.getcwd()
    skip_prefixes = [".claude/", ".obsidian/", ".git/"]
    suggest_mode = False
    files_filter: list[str] = []

    # Parse arguments
    i = 0
    while i < len(args):
        if args[i] == "--skip":
            i += 1
            skip_prefixes = []
            while i < len(args) and not args[i].startswith("-"):
                prefix = args[i]
                if not prefix.endswith("/"):
                    prefix += "/"
                skip_prefixes.append(prefix)
                i += 1
        elif args[i] == "--suggest":
            suggest_mode = True
            i += 1
        elif args[i] == "--files":
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                files_filter.append(args[i])
                i += 1
        else:
            workspace = os.path.abspath(args[i])
            i += 1

    if not os.path.isdir(workspace):
        print(f"ERROR: {workspace} is not a directory")
        sys.exit(2)

    all_files = collect_files(workspace)
    known_stems, known_paths, stem_to_file = build_known_names(all_files)

    if suggest_mode:
        if files_filter:
            ws_abs = os.path.abspath(workspace)
            normalized = set()
            for f in files_filter:
                f_abs = os.path.abspath(f) if os.path.isabs(f) else os.path.abspath(os.path.join(ws_abs, f))
                try:
                    rel = os.path.relpath(f_abs, ws_abs)
                except ValueError:
                    continue
                normalized.add(rel)
            scan_files = [f for f in all_files if f in normalized]
        else:
            scan_files = all_files
        suggestions = find_missing_wikilinks(
            workspace, scan_files, known_stems, stem_to_file, skip_prefixes
        )
        if suggestions:
            print(f"PLAIN TEXT REFERENCES ({len(suggestions)} found):")
            for f, line_num, text, stem in sorted(suggestions):
                print(f"  {f}:{line_num}: \"{text}\" -> [[{stem}]]")
        else:
            print("No plain text file references found - all references use wikilinks")
        sys.exit(0)
    else:
        broken = find_broken_links(workspace, all_files, known_stems, known_paths, skip_prefixes)
        closets_issues = find_closets_issues(workspace, all_files, known_stems, skip_prefixes)
        exit_code = 0
        if broken:
            print(f"BROKEN WIKILINKS ({len(broken)} found):")
            for f, link in sorted(broken):
                print(f"  {f}: [[{link}]]")
            exit_code = 1
        if closets_issues:
            print(f"CLOSETS ISSUES ({len(closets_issues)} found):")
            for f, line, msg in sorted(closets_issues):
                loc = f"{f}:{line}" if line else f
                print(f"  {loc}: {msg}")
            # Closets issues are warnings, not errors - don't fail CI on them alone
        if exit_code == 0 and not closets_issues:
            print("CLEAN - zero broken wikilinks, closets valid")
        elif exit_code == 0:
            print("CLEAN wikilinks (closets issues above are warnings)")
        sys.exit(exit_code)


def find_closets_issues(workspace, all_files, known_stems, skip_prefixes):
    """Validate _CLOSETS.md and _CLOSETS-archive.md structure across the workspace.

    Each `## [[stem]]` heading must reference a real file. Missing
    `<!-- memex-closets:N.N -->` marker is INFO, not an error.
    """
    issues = []
    for rel in all_files:
        if not _is_closets_file(rel):
            continue
        if any(rel.startswith(p) for p in skip_prefixes):
            continue
        full = os.path.join(workspace, rel)
        try:
            with open(full) as f:
                content = f.read()
        except Exception:
            continue
        if "<!-- memex-closets:" not in content:
            issues.append((rel, 0, "missing memex-closets version marker"))
        # Find headings of form "## [[stem]]"
        for line_num, line in enumerate(content.split("\n"), 1):
            m = re.match(r"##\s+\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]\s*$", line.strip())
            if not m:
                continue
            stem = os.path.splitext(m.group(1).strip())[0].lower()
            if stem not in known_stems:
                issues.append((rel, line_num, f"closet entry [[{m.group(1).strip()}]] points to missing file"))
    return issues


if __name__ == "__main__":
    main()
