"""
Tests for lsr.reasoning_tags — reasoning content removal, tag replacement, and formatting.
"""

import pytest

from lsr.reasoning_tags import (
    REASONING_END,
    REASONING_START,
    REASONING_TAG,
    format_reasoning_content,
    remove_reasoning_content,
    replace_reasoning_tags,
)

L = "\x3c"  # <
R = "\x3e"  # >


# ============================================================
# Constants
# ============================================================


class TestReasoningConstants:
    """Verify module-level constants are defined and non-empty."""

    def test_REASONING_TAG_is_nonempty_string(self):
        assert isinstance(REASONING_TAG, str)
        assert len(REASONING_TAG) > 0

    def test_REASONING_START_is_nonempty_string(self):
        assert isinstance(REASONING_START, str)
        assert len(REASONING_START) > 0

    def test_REASONING_END_is_nonempty_string(self):
        assert isinstance(REASONING_END, str)
        assert len(REASONING_END) > 0


# ============================================================
# remove_reasoning_content
# ============================================================


class TestRemoveReasoningContent:
    """Test removal of reasoning sections by tag."""

    @pytest.mark.parametrize("res", ["some text", "", "  "])
    def test_empty_tag_returns_res_unchanged(self, res):
        assert remove_reasoning_content(res, "") is res
        assert remove_reasoning_content(res, None) is res

    def test_no_tag_returns_unchanged(self):
        text = "hello world"
        assert remove_reasoning_content(text, "think") == "hello world"

    @pytest.mark.parametrize(
        "text,tag,expected",
        [
            (f"{L}think{R}reasoning{L}/think{R}answer", "think", "answer"),
            (f"{L}reason{R}thinking{L}/reason{R}output", "reason", "output"),
            (f"output{L}reason{R}thinking{L}/reason{R}", "reason", "output"),
            (f"pre{L}foo{R}mid{L}/foo{R}post", "foo", "prepost"),
        ],
    )
    def test_remove_single_complete_block(self, text, tag, expected):
        assert remove_reasoning_content(text, tag) == expected

    def test_remove_block_wraps_entire_text(self):
        assert remove_reasoning_content(f"{L}think{R}only{L}/think{R}", "think") == ""

    def test_remove_multiple_blocks(self):
        text = f"a{L}think{R}first{L}/think{R}" f"b{L}think{R}second{L}/think{R}c"
        assert remove_reasoning_content(text, "think") == "abc"

    def test_only_closing_tag_removes_preceding_content(self):
        text = f"prefix {L}/think{R} suffix"
        assert remove_reasoning_content(text, "think") == "suffix"

    def test_closing_tag_at_end_clears_all(self):
        text = f"everything before {L}/think{R}"
        assert remove_reasoning_content(text, "think") == ""

    def test_closing_tag_without_content_before(self):
        text = f"{L}/think{R}only after"
        assert remove_reasoning_content(text, "think") == "only after"

    def test_block_then_stray_closing_tag(self):
        """Full block removed by regex; leftover closing tag triggers deletion."""
        text = f"{L}think{R}a{L}/think{R} {L}/think{R}"
        assert remove_reasoning_content(text, "think") == ""

    def test_unclosed_opening_tag_kept(self):
        text = f"keep {L}think{R} this"
        assert remove_reasoning_content(text, "think") == f"keep {L}think{R} this"

    def test_other_tag_name_left_untouched(self):
        text = f"{L}foo{R}bar{L}/foo{R} {L}baz{R}qux{L}/baz{R}"
        # After removing <foo>...</foo>, strip() removes the leading space
        assert remove_reasoning_content(text, "foo") == f"{L}baz{R}qux{L}/baz{R}"

    def test_unicode_inside_tag(self):
        text = f"{L}think{R}\u00e9\u00e0\u00fc{L}/think{R}result"
        assert remove_reasoning_content(text, "think") == "result"

    def test_tag_regex_is_dotall(self):
        """DOTALL flag lets the regex span newlines."""
        text = f"{L}think{R}\nmulti\nline\n{L}/think{R}after"
        assert remove_reasoning_content(text, "think") == "after"


# ============================================================
# replace_reasoning_tags
# ============================================================


class TestReplaceReasoningTags:
    """Test replacing reasoning tags with formatted markers or removing them."""

    @pytest.mark.parametrize("text", [None, "", "  "])
    def test_empty_or_none_returns_as_is(self, text):
        assert replace_reasoning_tags(text, "think") is text

    def test_show_false_removes_content(self):
        text = f"{L}think{R}hidden{L}/think{R}visible"
        result = replace_reasoning_tags(text, "think", show=False)
        assert result == "visible"

    def test_show_false_no_tag_preserves(self):
        text = "no tags here"
        assert replace_reasoning_tags(text, "think", show=False) == "no tags here"

    def test_show_true_replaces_both_tags(self):
        text = f"{L}think{R}content{L}/think{R}"
        result = replace_reasoning_tags(text, "think", show=True)
        expected = f"\n{REASONING_START}\n\ncontent\n\n{REASONING_END}\n\n"
        assert result == expected

    def test_show_true_surrounding_whitespace_normalized(self):
        text = f"   {L}think{R}  data   {L}/think{R}  "
        result = replace_reasoning_tags(text, "think", show=True)
        # regex \s*<tag>\s* consumes surrounding whitespace from both the
        # opening AND closing passes, so "  data  " loses its outer spaces
        expected = f"\n{REASONING_START}\n\ndata\n\n{REASONING_END}\n\n"
        assert result == expected

    def test_show_true_only_opening_tag(self):
        text = f"pre {L}think{R}no closing"
        result = replace_reasoning_tags(text, "think", show=True)
        assert REASONING_START in result
        assert REASONING_END not in result

    def test_show_true_only_closing_tag(self):
        text = f"no opening {L}/think{R}"
        result = replace_reasoning_tags(text, "think", show=True)
        assert REASONING_START not in result
        assert REASONING_END in result

    def test_multiple_tags(self):
        text = f"{L}think{R}first{L}/think{R}" f"sep" f"{L}think{R}second{L}/think{R}"
        result = replace_reasoning_tags(text, "think", show=True)
        expected = (
            f"\n{REASONING_START}\n\nfirst\n\n{REASONING_END}\n\n"
            "sep"
            f"\n{REASONING_START}\n\nsecond\n\n{REASONING_END}\n\n"
        )
        assert result == expected

    def test_other_tag_not_touched(self):
        text = f"{L}other{R}keep{L}/other{R}"
        result = replace_reasoning_tags(text, "think", show=True)
        assert result == text


# ============================================================
# format_reasoning_content
# ============================================================


class TestFormatReasoningContent:
    """Test wrapping content inside reasoning tags."""

    @pytest.mark.parametrize("content", [None, ""])
    def test_empty_content_returns_empty_string(self, content):
        assert format_reasoning_content(content, "think") == ""

    def test_whitespace_only_is_truthy(self):
        """Whitespace is truthy, so it is wrapped (not returned empty)."""
        result = format_reasoning_content("  ", "think")
        assert result == f"{L}think{R}\n\n  \n\n{L}/think{R}"

    def test_wraps_content_with_tag(self):
        result = format_reasoning_content("hello", "think")
        assert result == f"{L}think{R}\n\nhello\n\n{L}/think{R}"

    def test_multiline_content(self):
        result = format_reasoning_content("line1\nline2", "reason")
        assert result == f"{L}reason{R}\n\nline1\nline2\n\n{L}/reason{R}"

    def test_different_tag_name(self):
        result = format_reasoning_content("data", "custom")
        assert result == f"{L}custom{R}\n\ndata\n\n{L}/custom{R}"

    def test_unicode_content(self):
        result = format_reasoning_content("\u00e9\u00e0\u00fc", "think")
        assert result == f"{L}think{R}\n\n\u00e9\u00e0\u00fc\n\n{L}/think{R}"
