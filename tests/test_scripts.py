"""
Free, deterministic tests for the Memex Python scripts.

These tests run on every push (no API keys needed) and exercise the
scripts that don't require an LLM:

  - verify-wikilinks.py (broken links, closets validation)
  - extract-graph.py (typed-edge graph from frontmatter)
  - sources.py (cross-workspace registry)

Run: python3 -m pytest tests/test_scripts.py -v
Or:  python3 tests/test_scripts.py  (no pytest required)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "memex" / "scripts"
VERIFY = SCRIPTS / "verify-wikilinks.py"
EXTRACT = SCRIPTS / "extract-graph.py"
SOURCES = SCRIPTS / "sources.py"


def run(cmd, cwd=None, expect_exit=0):
    """Run a subprocess; assert exit code; return stdout."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == expect_exit, (
        f"Expected exit {expect_exit}, got {result.returncode}.\n"
        f"cmd={cmd}\n"
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}"
    )
    return result.stdout


# --- verify-wikilinks ------------------------------------------------------

def test_verify_wikilinks_clean():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "alpha.md").write_text("# Alpha\nLink to [[beta]].")
        (p / "beta.md").write_text("# Beta\nBack to [[alpha]].")
        out = run([sys.executable, str(VERIFY), str(p)])
        assert "CLEAN" in out


def test_verify_wikilinks_broken():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "alpha.md").write_text("# Alpha\nLink to [[ghost]].")
        out = run([sys.executable, str(VERIFY), str(p)], expect_exit=1)
        assert "BROKEN" in out
        assert "ghost" in out


def test_verify_wikilinks_closets_dangling():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "alpha.md").write_text("# Alpha")
        (p / "_CLOSETS.md").write_text(
            "# Closets: test\n<!-- memex-closets:1.0 -->\n\n"
            "## [[alpha]]\n- subjects: foo\n\n"
            "## [[ghost]]\n- subjects: bar\n"
        )
        out = run([sys.executable, str(VERIFY), str(p)])
        assert "ghost" in out
        assert "missing file" in out


def test_verify_wikilinks_closets_archive_dangling():
    """_CLOSETS-archive.md is validated the same way as _CLOSETS.md."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "alpha.md").write_text("# Alpha")
        (p / "_CLOSETS.md").write_text(
            "# Closets: test\n<!-- memex-closets:1.1 -->\n\n## [[alpha]]\n- subjects: foo\n"
        )
        (p / "_CLOSETS-archive.md").write_text(
            "# Closets archive: test\n<!-- memex-closets:1.1 -->\n\n"
            "## [[ghost-archived]]\n- subjects: bar\n"
        )
        out = run([sys.executable, str(VERIFY), str(p)])
        assert "ghost-archived" in out
        assert "missing file" in out


def test_verify_wikilinks_closets_archive_clean():
    """A clean _CLOSETS-archive.md should not report issues."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "alpha.md").write_text("# Alpha")
        (p / "beta.md").write_text("# Beta")
        (p / "_CLOSETS.md").write_text(
            "# Closets: test\n<!-- memex-closets:1.1 -->\n\n## [[alpha]]\n- subjects: foo\n"
        )
        (p / "_CLOSETS-archive.md").write_text(
            "# Closets archive: test\n<!-- memex-closets:1.1 -->\n\n## [[beta]]\n- subjects: bar\n"
        )
        out = run([sys.executable, str(VERIFY), str(p)])
        assert "missing file" not in out


# --- extract-graph ---------------------------------------------------------

def test_extract_graph_basic():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "decision-1.md").write_text(
            "---\ntype: decision\nsupersedes: [[decision-0]]\npeople: [[Alice]]\n---\n# Decision"
        )
        (p / "decision-0.md").write_text(
            "---\ntype: decision\nstatus: superseded\n---\n# Old"
        )
        (p / "alice.md").write_text("# Alice")
        out = run([sys.executable, str(EXTRACT), str(p), "--print"])
        assert "supersedes" in out
        assert "decision-1" in out
        assert "people" in out


def test_extract_graph_dangling():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "a.md").write_text(
            "---\ntype: decision\nsupersedes: [[ghost]]\n---\n# A"
        )
        out = run([sys.executable, str(EXTRACT), str(p), "--check"], expect_exit=1)
        assert "ghost" in out


def test_extract_graph_no_frontmatter():
    """Files without frontmatter should not show up — purely additive."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "plain.md").write_text("# Plain markdown, no frontmatter\nSome content.")
        out = run([sys.executable, str(EXTRACT), str(p), "--print"])
        assert "0 typed edges" in out or "0/1" in out


# --- sources.py ------------------------------------------------------------

def test_sources_lifecycle(tmp_home_for_sources):
    home = tmp_home_for_sources
    with tempfile.TemporaryDirectory() as ws:
        (Path(ws) / "_MANIFEST.md").write_text("# m")
        env = {**os.environ, "HOME": str(home)}
        # add
        result = subprocess.run(
            [sys.executable, str(SOURCES), "add", "test-src", ws],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
        # list
        result = subprocess.run(
            [sys.executable, str(SOURCES), "list"],
            capture_output=True, text=True, env=env,
        )
        assert "test-src" in result.stdout
        # search (no matches expected against empty manifest)
        result = subprocess.run(
            [sys.executable, str(SOURCES), "search", "fundraising"],
            capture_output=True, text=True, env=env,
        )
        assert "test-src" in result.stdout or "Total hits: 0" in result.stdout
        # remove
        result = subprocess.run(
            [sys.executable, str(SOURCES), "remove", "test-src"],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0


def test_sources_search_local_groups_by_folder(tmp_home_for_sources):
    """search-local should grep manifest + closets in the workspace and group results by folder."""
    with tempfile.TemporaryDirectory() as ws:
        ws_path = Path(ws)
        (ws_path / "_MANIFEST.md").write_text("# m\n")
        (ws_path / "programs").mkdir()
        (ws_path / "programs" / "_CLOSETS.md").write_text(
            "# Closets: programs\n<!-- memex-closets:1.1 -->\n"
            "## [[after-school]]\n- people: [[Mike]]\n"
        )
        (ws_path / "memory").mkdir()
        (ws_path / "memory" / "_CLOSETS.md").write_text(
            "# Closets: memory\n<!-- memex-closets:1.1 -->\n"
            "## [[status]]\n- subjects: Mike's leave\n"
        )
        result = subprocess.run(
            [sys.executable, str(SOURCES), "search-local", "Mike", "--workspace", ws],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "=== programs ===" in result.stdout
        assert "=== memory ===" in result.stdout
        assert "Total hits" in result.stdout


# --- pytest fixtures (only used if pytest is available) -------------------

try:
    import pytest

    @pytest.fixture
    def tmp_home_for_sources(tmp_path):
        return tmp_path
except ImportError:  # pragma: no cover
    pass


# --- standalone runner -----------------------------------------------------

def main_standalone():
    """Run all tests without pytest. Useful for CI without pytest dep."""
    tests = [
        ("verify_wikilinks_clean", test_verify_wikilinks_clean),
        ("verify_wikilinks_broken", test_verify_wikilinks_broken),
        ("verify_wikilinks_closets_dangling", test_verify_wikilinks_closets_dangling),
        ("verify_wikilinks_closets_archive_dangling", test_verify_wikilinks_closets_archive_dangling),
        ("verify_wikilinks_closets_archive_clean", test_verify_wikilinks_closets_archive_clean),
        ("extract_graph_basic", test_extract_graph_basic),
        ("extract_graph_dangling", test_extract_graph_dangling),
        ("extract_graph_no_frontmatter", test_extract_graph_no_frontmatter),
    ]
    # sources tests use a fixture; run them manually
    def run_sources_test():
        with tempfile.TemporaryDirectory() as home:
            test_sources_lifecycle(Path(home))
    tests.append(("sources_lifecycle", run_sources_test))

    def run_sources_search_local_test():
        with tempfile.TemporaryDirectory() as home:
            test_sources_search_local_groups_by_folder(Path(home))
    tests.append(("sources_search_local_groups_by_folder", run_sources_search_local_test))

    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failures += 1
            print(f"  ✗ {name}\n      {e}")
        except Exception as e:
            failures += 1
            print(f"  ✗ {name}  ({type(e).__name__}: {e})")
    print(f"\n{len(tests) - failures}/{len(tests)} passed.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main_standalone()
