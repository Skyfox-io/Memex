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


def find_broken_links(workspace, all_files, known_stems, known_paths, skip_prefixes):
    """Find all broken wikilinks in markdown files."""
    broken = []

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
        else:
            workspace = os.path.abspath(args[i])
            i += 1

    if not os.path.isdir(workspace):
        print(f"ERROR: {workspace} is not a directory")
        sys.exit(2)

    all_files = collect_files(workspace)
    known_stems, known_paths, stem_to_file = build_known_names(all_files)

    if suggest_mode:
        suggestions = find_missing_wikilinks(
            workspace, all_files, known_stems, stem_to_file, skip_prefixes
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
        if broken:
            print(f"BROKEN WIKILINKS ({len(broken)} found):")
            for f, link in sorted(broken):
                print(f"  {f}: [[{link}]]")
            sys.exit(1)
        else:
            print("CLEAN - zero broken wikilinks")
            sys.exit(0)


if __name__ == "__main__":
    main()
