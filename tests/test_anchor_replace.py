"""Tests for lsr.coders.anchor_replace module.

Tests pure-logic functions: similarity, find_anchor_match, anchor_replace,
parse_anchor_blocks, and apply_anchor_edits (with tmp_path for filesystem ops).
"""

import pytest
from lsr.coders.anchor_replace import (
    similarity,
    find_anchor_match,
    anchor_replace,
    parse_anchor_blocks,
    apply_anchor_edits,
)


class TestSimilarity:
    @pytest.mark.parametrize(
        "a, b, expected_min",
        [
            ("hello", "hello", 1.0),
            ("", "", 1.0),
            ("abc", "xyz", 0.0),
            ("", "nonempty", 0.0),
            ("python", "py", 0.4),
        ],
    )
    def test_similarity(self, a, b, expected_min):
        result = similarity(a, b)
        assert 0.0 <= result <= 1.0
        assert result >= expected_min - 0.001

    def test_similarity_symmetric(self):
        assert similarity("abc", "xyz") == similarity("xyz", "abc")


class TestFindAnchorMatch:
    def test_exact_head_and_tail(self):
        content = "The quick brown fox jumps over the lazy dog."
        head = "The quick"
        tail = "lazy dog"
        start, end = find_anchor_match(content, head, tail)
        assert start == content.find(head)
        assert end == content.find(tail) + len(tail)

    def test_head_fuzzy_tail_exact(self):
        """Head not found exactly but fuzzy match > 0.6 picks closest line.
        start points to the fuzzy-matched full line, end includes tail."""
        content = "First line.\nThe brown fox moves fast.\nThird line.\nLazy dog sleeps."
        head = "The brown fox jumps"
        tail = "Lazy dog sleeps"
        start, end = find_anchor_match(content, head, tail)
        assert start is not None
        assert end is not None
        # start should point to the fuzzy-matched line
        assert content[start:].startswith("The brown fox")
        # end should include the tail
        assert content[end - len(tail) : end] == tail

    def test_head_exact_tail_fuzzy(self):
        """Tail not exact but fuzzy match > 0.6 picks closest line.
        The function returns end = tail_pos + len(original tail_anchor)."""
        content = "Alpha\nBeta gamma delta\nOmega"
        head = "Alpha"
        tail = "Omega xyz"  # fuzzy matches "Omega" (score ~0.71)
        start, end = find_anchor_match(content, head, tail)
        assert start is not None
        assert end is not None
        # start points to head
        assert content[start : start + len(head)] == head
        # tail_pos is where "Omega" appears in content
        tail_pos = content.find("Omega", start + len(head))
        assert tail_pos >= 0
        # end = tail_pos + len(tail_anchor)
        assert end > tail_pos

    def test_both_not_found(self):
        content = "First line.\nSecond line."
        start, end = find_anchor_match(content, "MIA_head", "MIA_tail")
        assert start is None
        assert end is None

    def test_tail_before_head(self):
        """Tail appears before head — find_anchor_match searches tail after
        head_pos so it should miss and return None, None."""
        content = "Tail here. Middle. Head here."
        head = "Head here"
        tail = "Tail here"
        start, end = find_anchor_match(content, head, tail)
        assert start is None
        assert end is None

    def test_empty_content(self):
        start, end = find_anchor_match("", "any", "any")
        assert start is None
        assert end is None

    def test_fuzzy_both_not_found(self):
        content = "Alpha.\nBeta.\nGamma."
        start, end = find_anchor_match(content, "ZZZZZZZZZ_no_match", "YYYYYY_no_match")
        assert start is None
        assert end is None

    def test_tail_whitespace_drift(self):
        """Tail anchor carries drifted trailing whitespace; stripped match recovers (A3)."""
        content = "First sentence. Middle content. Last sentence.\n"
        start, end = find_anchor_match(content, "First sentence.", "Last sentence ")
        assert start == 0
        assert content[start:end] == "First sentence. Middle content. Last sentence"

    def test_missing_tail_anchor_eof(self):
        """Tail anchor genuinely absent -> replace head through end of content (A3)."""
        content = "First sentence. Middle content. Last sentence.\n"
        start, end = find_anchor_match(content, "First sentence.", "Nonexistent tail.")
        assert start == 0
        assert end == len(content)

    def test_tail_before_head_still_fails(self):
        """Tail present but before head is an ordering error, not a missing tail -> fail."""
        content = "Tail here. Middle. Head here."
        start, end = find_anchor_match(content, "Head here", "Tail here")
        assert start is None
        assert end is None


class TestAnchorReplace:
    def test_basic_replacement(self):
        content = "Before AAA after."
        result = anchor_replace(content, "AAA", "after", "XYZ")
        assert result == "Before XYZ."

    def test_anchors_not_found(self):
        content = "Some content."
        result = anchor_replace(content, "MISSING", "ALSO_MISSING", "NEW")
        assert result is None

    def test_preserve_before_and_after(self):
        content = "prefix-<<<BODY>>>-suffix"
        result = anchor_replace(content, "<<<BODY>>>", "-suffix", "new_mid")
        assert result == "prefix-new_mid"

    def test_replacement_with_newlines(self):
        content = "line1\nANCHOR\nline3"
        result = anchor_replace(content, "ANCHOR", "line3", "REPLACED\nX")
        assert result == "line1\nREPLACED\nX"

    def test_fuzzy_anchor_replace(self):
        """Head matched via fuzzy finder, tail exact.
        Use a head that is NOT a substring of the content."""
        content = "intro\nThe quick brown fox jumps.\nending"
        # "brown fox jumps!!!" fuzzy-matches "The quick brown fox jumps." (score 0.69)
        result = anchor_replace(content, "brown fox jumps!!!", "ending", "NEW_BODY")
        assert result is not None
        assert "fox jumps" not in result
        assert "NEW_BODY" in result
        assert result == "intro\nNEW_BODY"


class TestParseAnchorBlocks:
    def test_single_block(self):
        text = (
            "<<<<<<< ANCHOR: head1\n"
            ">>>>>>> REPLACE\n"
            "new content\n"
            "<<<<<<< ANCHOR: tail1\n"
            ">>>>>>> END"
        )
        blocks = parse_anchor_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["head"] == "head1"
        assert blocks[0]["tail"] == "tail1"
        assert blocks[0]["replacement"] == "new content"

    def test_multiple_blocks(self):
        text = (
            "<<<<<<< ANCHOR: h1\n"
            ">>>>>>> REPLACE\n"
            "r1\n"
            "<<<<<<< ANCHOR: t1\n"
            ">>>>>>> END\n"
            "<<<<<<< ANCHOR: h2\n"
            ">>>>>>> REPLACE\n"
            "r2\n"
            "<<<<<<< ANCHOR: t2\n"
            ">>>>>>> END"
        )
        blocks = parse_anchor_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]["head"] == "h1"
        assert blocks[0]["replacement"] == "r1"
        assert blocks[0]["tail"] == "t1"
        assert blocks[1]["head"] == "h2"
        assert blocks[1]["replacement"] == "r2"
        assert blocks[1]["tail"] == "t2"

    def test_body_with_newlines(self):
        text = (
            "<<<<<<< ANCHOR: h\n"
            ">>>>>>> REPLACE\n"
            "line1\n"
            "line2\n"
            "line3\n"
            "<<<<<<< ANCHOR: t\n"
            ">>>>>>> END"
        )
        blocks = parse_anchor_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["replacement"] == "line1\nline2\nline3"

    def test_no_match_empty_list(self):
        assert parse_anchor_blocks("Just some random text with no blocks.") == []

    def test_empty_text(self):
        assert parse_anchor_blocks("") == []

    def test_leading_surrounding_text_ignored(self):
        text = (
            "before\n"
            "<<<<<<< ANCHOR: h\n"
            ">>>>>>> REPLACE\n"
            "body\n"
            "<<<<<<< ANCHOR: t\n"
            ">>>>>>> END\n"
            "after"
        )
        blocks = parse_anchor_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["head"] == "h"
        assert blocks[0]["tail"] == "t"
        assert blocks[0]["replacement"] == "body"


class TestApplyAnchorEdits:
    def test_basic_success(self, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text("AAA-old-BBB-old-CCC")
        edits = [{"head": "AAA", "tail": "BBB-old-CCC", "replacement": "AAA-NEW-BBB-NEW-CCC"}]
        ok, new_content, err = apply_anchor_edits(str(f), edits)
        assert ok is True
        assert new_content == "AAA-NEW-BBB-NEW-CCC"
        assert err is None

    def test_multiple_edits(self, tmp_path):
        """Two disjoint edits where each edit's anchors only appear once."""
        f = tmp_path / "multi.tex"
        f.write_text("a <<<ONE>>> b <<<TWO>>> c end")
        edits = [
            {"head": "<<<ONE>>>", "tail": "b ", "replacement": "REPLACED_ONE "},
            {"head": "<<<TWO>>>", "tail": "c ", "replacement": "REPLACED_TWO "},
        ]
        ok, new_content, err = apply_anchor_edits(str(f), edits)
        assert ok is True
        assert new_content == "a REPLACED_ONE REPLACED_TWO end"
        assert err is None

    def test_all_edits_fail(self, tmp_path):
        f = tmp_path / "nomatch.tex"
        f.write_text("Some content")
        edits = [{"head": "MIA", "tail": "GONE", "replacement": "x"}]
        ok, new_content, err = apply_anchor_edits(str(f), edits)
        assert ok is False
        assert new_content is None
        assert err == "No edits could be applied"

    def test_file_not_found(self, tmp_path):
        edits = [{"head": "a", "tail": "b", "replacement": "c"}]
        ok, new_content, err = apply_anchor_edits(str(tmp_path / "nonexistent.txt"), edits)
        assert ok is False
        assert new_content is None
        assert err is not None
        assert "No such file" in err or "does not exist" in err or "not found" in err or err
