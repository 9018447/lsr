"""Tests for crg_toolkit.py search functionality."""

import argparse
from unittest.mock import MagicMock

from aider.crg_toolkit import _search_relevance_score, cmd_search


def _make_node(name, qualified_name=None, file_path="test.py", kind="Function"):
    """Helper to create a mock node."""
    node = MagicMock()
    node.name = name
    node.qualified_name = qualified_name or f"module::{name}"
    node.file_path = file_path
    node.kind = kind
    node.display_name = name
    node.short_path = file_path
    node.line_start = 1
    return node


def _make_args(pattern, limit=20, verbose=False):
    """Helper to create argparse.Namespace for search."""
    return argparse.Namespace(pattern=pattern, limit=limit, verbose=verbose)


class TestSearchRelevanceScore:
    def test_exact_name_match(self):
        node = _make_node("search")
        assert _search_relevance_score(node, "search") == 100

    def test_name_starts_with(self):
        node = _make_node("search_node")
        assert _search_relevance_score(node, "search") == 80

    def test_name_contains(self):
        node = _make_node("cmd_search")
        assert _search_relevance_score(node, "search") == 60

    def test_qualified_name_contains(self):
        node = _make_node("something", qualified_name="module::search_func")
        assert _search_relevance_score(node, "search") == 40

    def test_file_path_contains(self):
        node = _make_node("other", file_path="search_utils.py")
        assert _search_relevance_score(node, "search") == 20

    def test_case_insensitive(self):
        node = _make_node("Search")
        assert _search_relevance_score(node, "search") == 100

    def test_partial_match_in_name(self):
        node = _make_node("binary_search")
        score = _search_relevance_score(node, "search")
        assert score == 60  # name contains pattern


class TestCmdSearch:
    def test_no_matches(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("foo"), _make_node("bar")]
        args = _make_args("nonexistent")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "No matches for" in captured.out

    def test_single_match(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("search"), _make_node("other")]
        args = _make_args("search")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 1 match" in captured.out
        assert "search" in captured.out

    def test_multiple_matches_sorted_by_relevance(self, capsys):
        cm = MagicMock()
        cm.nodes = [
            _make_node("cmd_search", kind="Function"),  # name contains = 60
            _make_node("search", kind="Function"),  # exact match = 100
            _make_node("search_utils", kind="Module"),  # name starts = 80
        ]
        args = _make_args("search")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 3 match" in captured.out

        # Check order: search (100) > search_utils (80) > cmd_search (60)
        lines = captured.out.strip().split("\n")
        result_lines = [line for line in lines if "[" in line and "]" in line]
        assert len(result_lines) == 3
        assert "search" in result_lines[0]
        assert "search_utils" in result_lines[1]
        assert "cmd_search" in result_lines[2]

    def test_limit_results(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node(f"item_{i}") for i in range(30)]
        args = _make_args("item", limit=5)

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "... and 25 more" in captured.out

    def test_verbose_shows_qualified_name(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("test", qualified_name="module::test")]
        args = _make_args("test", verbose=True)

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "qn: module::test" in captured.out

    def test_always_shows_qualified_name(self, capsys):
        """qualified_name should always be shown, not just in verbose mode."""
        cm = MagicMock()
        cm.nodes = [_make_node("test", qualified_name="module::test")]
        args = _make_args("test", verbose=False)

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "qn: module::test" in captured.out

    def test_search_by_qualified_name(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("foo", qualified_name="mymodule::bar")]
        args = _make_args("bar")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 1 match" in captured.out

    def test_search_by_file_path(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("foo", file_path="src/search.py")]
        args = _make_args("search.py")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 1 match" in captured.out

    def test_empty_pattern(self, capsys):
        """Empty pattern should match everything."""
        cm = MagicMock()
        cm.nodes = [_make_node("foo"), _make_node("bar")]
        args = _make_args("")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 2 match" in captured.out

    def test_special_characters_in_pattern(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("__init__", qualified_name="module::__init__")]
        args = _make_args("__init__")

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 1 match" in captured.out


def _make_fuzzy_args(pattern, limit=20, fuzzy=False, threshold=0.6):
    """Helper to create argparse.Namespace for fuzzy search."""
    return argparse.Namespace(
        pattern=pattern, limit=limit, verbose=False, fuzzy=fuzzy, threshold=threshold
    )


class TestFuzzySearch:
    def test_fuzzy_match_similar_names(self, capsys):
        cm = MagicMock()
        cm.nodes = [
            _make_node("binary_search"),
            _make_node("linear_search"),
            _make_node("sort"),
        ]
        args = _make_fuzzy_args("serch", fuzzy=True, threshold=0.5)

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        # "serch" should fuzzy match "search" in binary_search and linear_search
        assert "Found" in captured.out

    def test_fuzzy_no_match_below_threshold(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("completely_different")]
        args = _make_fuzzy_args("xyz", fuzzy=True, threshold=0.8)

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "No matches" in captured.out

    def test_fuzzy_disabled_uses_substring(self, capsys):
        cm = MagicMock()
        cm.nodes = [_make_node("search_function")]
        args = _make_fuzzy_args("search", fuzzy=False)

        result = cmd_search(cm, args)
        captured = capsys.readouterr()

        assert result == 0
        assert "Found 1 match" in captured.out

    def test_fuzzy_match_score(self):
        from aider.crg_toolkit import _fuzzy_match_score

        # Exact match
        assert _fuzzy_match_score("search", "search") == 1.0

        # Similar strings
        score = _fuzzy_match_score("search", "serch")
        assert score > 0.6

        # Completely different
        score = _fuzzy_match_score("hello", "xyz")
        assert score < 0.3

        # Empty strings
        assert _fuzzy_match_score("", "test") == 0.0
        assert _fuzzy_match_score("test", "") == 0.0


from aider.crg_tool_adapter import is_graph_db_stale, setup_git_hooks
import os


class TestAutoRefresh:
    def test_is_graph_db_stale_no_db(self, tmp_path):
        """Database is stale when it doesn't exist."""
        assert is_graph_db_stale(tmp_path) is True

    def test_is_graph_db_stale_with_db(self, tmp_path):
        """Database is not stale when newer than git."""
        # Create a fake db file
        db_dir = tmp_path / ".code-review-graph"
        db_dir.mkdir()
        db_file = db_dir / "graph.db"
        db_file.touch()
        # Without git, should return False
        assert is_graph_db_stale(tmp_path) is False

    def test_setup_git_hooks_creates_hooks(self, tmp_path):
        """setup_git_hooks creates post-commit and post-merge hooks."""
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        result = setup_git_hooks(tmp_path)
        assert result is True
        assert (hooks_dir / "post-commit").exists()
        assert (hooks_dir / "post-merge").exists()
        # Check executable
        assert os.access(hooks_dir / "post-commit", os.X_OK)

    def test_setup_git_hooks_no_overwrite(self, tmp_path):
        """setup_git_hooks doesn't overwrite existing hooks."""
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook_path = hooks_dir / "post-commit"
        hook_path.write_text("#!/bin/sh\necho existing")
        setup_git_hooks(tmp_path)
        assert "existing" in hook_path.read_text()

    def test_setup_git_hooks_no_git_dir(self, tmp_path):
        """setup_git_hooks returns False without .git directory."""
        result = setup_git_hooks(tmp_path)
        assert result is False
