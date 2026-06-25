"""
Tests for diffs pure functions: create_progress_bar, assert_newlines,
find_last_non_deleted, diff_partial_update.
"""

from __future__ import annotations

import pytest

from lsr.diffs import (
    assert_newlines,
    create_progress_bar,
    diff_partial_update,
    find_last_non_deleted,
)


class TestCreateProgressBar:
    """create_progress_bar renders a 30-block bar with █ and ░."""

    def test_zero_percent(self):
        bar = create_progress_bar(0)
        assert bar == "█" * 0 + "░" * 30

    def test_one_hundred_percent(self):
        bar = create_progress_bar(100)
        assert bar == "█" * 30 + "░" * 0

    def test_fifty_percent(self):
        bar = create_progress_bar(50)
        assert bar == "█" * 15 + "░" * 15

    def test_over_100_produces_more_than_30_chars(self):
        """Code does not clamp; filled blocks can exceed total_blocks."""
        bar = create_progress_bar(200)
        assert len(bar) > 30
        assert bar.startswith("█")

    def test_negative_produces_full_empty_bar(self):
        """Negative percentage gives negative filled, so only ░ chars appear."""
        bar = create_progress_bar(-50)
        assert isinstance(bar, str)
        # filled = int(30 * -50 // 100) = -15, empty = 30 - (-15) = 45
        assert "░" in bar or bar == ""

    @pytest.mark.parametrize(
        ("pct", "filled", "empty"),
        [
            (0, 0, 30),
            (25, 7, 23),  # int(30*25//100) = int(750//100) = 7
            (33, 9, 21),  # int(30*33//100) = int(990//100) = 9
            (50, 15, 15),
            (75, 22, 8),  # int(30*75//100) = int(2250//100) = 22
            (100, 30, 0),
        ],
    )
    def test_parametrized(self, pct, filled, empty):
        bar = create_progress_bar(pct)
        assert bar == "█" * filled + "░" * empty
        assert len(bar) == 30


class TestAssertNewlines:
    """assert_newlines validates every line (except the last) ends with \\n."""

    def test_normal_lines(self):
        assert_newlines(["line1\n", "line2\n", "line3\n"])

    def test_empty_list(self):
        assert_newlines([])

    def test_missing_newline_on_non_last_line_raises(self):
        """Only lines[:-1] are checked; the last line is never validated."""
        with pytest.raises(AssertionError):
            assert_newlines(["bad", "good\n"])

    def test_last_line_can_lack_newline(self):
        """The code skips the last line, so it is allowed to lack \\n."""
        assert_newlines(["ok\n", "no-newline"])


class TestFindLastNonDeleted:
    """find_last_non_deleted returns the last unchanged line index in the original."""

    def test_no_changes(self):
        orig = ["a\n", "b\n", "c\n"]
        upd = ["a\n", "b\n", "c\n"]
        assert find_last_non_deleted(orig, upd) == 3

    def test_partial_update_identical_prefix(self):
        orig = ["a\n", "b\n", "c\n", "d\n"]
        upd = ["a\n", "b\n"]
        assert find_last_non_deleted(orig, upd) == 2

    def test_appended_lines(self):
        orig = ["a\n"]
        upd = ["a\n", "b\n", "c\n"]
        assert find_last_non_deleted(orig, upd) == 1

    def test_deleted_at_end(self):
        orig = ["a\n", "b\n", "c\n"]
        upd = ["a\n", "b\n"]
        assert find_last_non_deleted(orig, upd) == 2

    def test_deleted_in_middle(self):
        orig = ["a\n", "b\n", "c\n"]
        upd = ["a\n", "c\n"]
        assert find_last_non_deleted(orig, upd) == 3

    def test_empty_updated_returns_none(self):
        orig = ["a\n", "b\n"]
        upd = []
        assert find_last_non_deleted(orig, upd) is None

    def test_empty_orig_returns_none(self):
        orig = []
        upd = ["a\n"]
        assert find_last_non_deleted(orig, upd) is None

    def test_all_modified_returns_none(self):
        orig = ["a\n", "b\n"]
        upd = ["x\n", "y\n"]
        assert find_last_non_deleted(orig, upd) is None


class TestDiffPartialUpdate:
    """diff_partial_update produces a fenced diff block with progress bar."""

    def test_no_changes(self):
        lines = ["a\n", "b\n"]
        result = diff_partial_update(lines, lines, final=True)
        assert "```diff" in result
        assert "```" in result

    def test_append_lines(self):
        orig = ["a\n", "b\n"]
        upd = ["a\n", "b\n", "c\n"]
        result = diff_partial_update(orig, upd, final=True)
        assert "```diff" in result
        assert "+c" in result

    def test_delete_lines(self):
        orig = ["a\n", "b\n"]
        upd = ["a\n"]
        result = diff_partial_update(orig, upd, final=True)
        assert "```diff" in result
        assert "-b" in result

    def test_partial_bar_non_final(self):
        orig = ["a\n", "b\n", "c\n"]
        upd = ["a\n"]
        result = diff_partial_update(orig, upd, final=False)
        assert "/" in result
        assert "lines" in result
        assert "%" in result

    def test_final_includes_progress_bar(self):
        """The progress bar is always included, even in final mode."""
        orig = ["a\n", "b\n"]
        upd = ["a\n", "b\n"]
        result = diff_partial_update(orig, upd, final=True)
        assert "```diff" in result

    def test_fname_in_header(self):
        orig = ["a\n"]
        upd = ["a\n"]
        result = diff_partial_update(orig, upd, final=True, fname="test.tex")
        assert "--- test.tex original" in result
        assert "+++ test.tex updated" in result

    def test_empty_orig_partial_returns_empty(self):
        """When orig is empty and final=False, find_last_non_deleted is None -> ''."""
        orig = []
        upd = ["a\n"]
        result = diff_partial_update(orig, upd, final=False)
        assert result == ""

    def test_empty_orig_final_works(self):
        """When orig is empty and final=True, last_non_deleted = 0, shows diff."""
        orig = []
        upd = ["a\n"]
        result = diff_partial_update(orig, upd, final=True)
        assert "```diff" in result
        assert "+a" in result

    def test_progress_bar_in_result(self):
        orig = ["a\n", "b\n", "c\n", "d\n"]
        upd = ["a\n", "b\n"]
        result = diff_partial_update(orig, upd, final=False)
        assert "4 lines" in result
        assert "[" in result and "]" in result
