"""Tests for edit-application observability and fallback tagging."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from lsr.coders.anchor_replace import anchor_replace_with_tag
from lsr.coders.edit_log import EditLog, FallbackTag, VALID_TAGS
from lsr.coders.editblock_coder import (
    do_replace_with_tag,
    replace_most_similar_chunk_with_tag,
)


class TestFallbackTags:
    """Fallback tags are drawn from the fixed enum."""

    def test_all_documented_tags_present(self):
        documented = {
            "perfect",
            "whitespace",
            "unicode",
            "latex-escape",
            "ignore-linebreaks",
            "prefix",
            "missing-whitespace",
            "edit-distance",
            "similar-lines",
            "anchor-headtail",
        }
        assert documented <= VALID_TAGS


class TestReplaceMostSimilarChunkWithTag:
    """Matcher functions return the fallback that handled the match."""

    def test_perfect_match_returns_perfect_tag(self):
        whole = "line one\nline two\nline three\n"
        search = "line two\n"
        replace = "LINE TWO\n"
        content, tag = replace_most_similar_chunk_with_tag(whole, search, replace)
        assert "LINE TWO" in content
        assert tag == FallbackTag.PERFECT

    def test_missing_leading_whitespace_tag(self):
        whole = "    indented line\n"
        search = "indented line\n"
        replace = "INDENTED LINE\n"
        content, tag = replace_most_similar_chunk_with_tag(whole, search, replace)
        assert "INDENTED LINE" in content
        assert tag == FallbackTag.MISSING_WHITESPACE

    def test_ignore_linebreaks_tag(self):
        whole = "This is a single long line in the file.\n"
        search = "This is\na single long line\nin the file.\n"
        replace = "This becomes\na single long line\nin the file.\n"
        content, tag = replace_most_similar_chunk_with_tag(whole, search, replace)
        assert "This becomes" in content
        assert tag == FallbackTag.IGNORE_LINEBREAKS

    def test_prefix_match_tag(self):
        # Multi-line SEARCH that is a prefix of the file chunk; ignore-linebreaks
        # fails because the joined search spans file lines without matching a
        # single line exactly.
        whole = "line one starts here and continues\nonto line two with more text.\n"
        search = "line one starts here\nand continues onto line two"
        replace = "LINE ONE STARTS HERE\nAND CONTINUES ONTO LINE TWO"
        content, tag = replace_most_similar_chunk_with_tag(whole, search, replace)
        assert "LINE ONE STARTS HERE" in content
        assert "with more text" in content
        assert tag == FallbackTag.PREFIX

    def test_edit_distance_tag(self):
        whole = "The quick brown fox jumps over the lazy dog.\n"
        search = "The quikc brown fox jumps over the lzy dog.\n"
        replace = "The quick brown fox jumps over the lazy cat.\n"
        content, tag = replace_most_similar_chunk_with_tag(whole, search, replace)
        assert content is not None
        assert "lazy cat" in content
        assert tag == FallbackTag.EDIT_DISTANCE

    def test_failure_returns_edit_distance_tag(self):
        whole = "Completely unrelated content here.\n"
        search = "This text does not exist anywhere.\n"
        replace = "Replacement text.\n"
        content, tag = replace_most_similar_chunk_with_tag(whole, search, replace)
        assert content is None
        assert tag == FallbackTag.EDIT_DISTANCE


class TestDoReplaceWithTag:
    """do_replace_with_tag reports the matcher fallback."""

    def test_do_replace_perfect_tag(self, tmp_path):
        fpath = tmp_path / "test.tex"
        fpath.write_text("Hello world.\n", encoding="utf-8")
        content, tag = do_replace_with_tag(
            fpath, fpath.read_text(encoding="utf-8"), "Hello world.", "Goodbye world."
        )
        assert "Goodbye world" in content
        assert tag == FallbackTag.PERFECT

    def test_do_replace_appends_with_perfect_tag(self, tmp_path):
        fpath = tmp_path / "test.tex"
        fpath.write_text("Hello world.\n", encoding="utf-8")
        content, tag = do_replace_with_tag(
            fpath, fpath.read_text(encoding="utf-8"), "", "More text.\n"
        )
        assert "More text" in content
        assert tag == FallbackTag.PERFECT


class TestAnchorReplaceWithTag:
    """Anchor replacement reports the anchor-headtail fallback."""

    def test_anchor_replace_success(self):
        content = "First sentence. Middle content. Last sentence.\n"
        new_content, tag = anchor_replace_with_tag(
            content, "First sentence.", "Last sentence.", "Replacement."
        )
        assert "Replacement." in new_content
        assert tag == FallbackTag.ANCHOR_HEADTAIL

    def test_anchor_replace_failure(self):
        content = "First sentence. Middle content. Last sentence.\n"
        new_content, tag = anchor_replace_with_tag(
            content, "Missing head.", "Missing tail.", "Replacement."
        )
        assert new_content is None
        assert tag == FallbackTag.ANCHOR_HEADTAIL

    def test_anchor_tail_whitespace_drift_tag(self):
        """A3: drifted trailing whitespace on the tail reports a distinct tag."""
        content = "First sentence. Middle content. Last sentence.\n"
        new_content, tag = anchor_replace_with_tag(
            content, "First sentence.", "Last sentence ", "Replacement."
        )
        assert new_content is not None
        assert tag == FallbackTag.ANCHOR_TAIL_WHITESPACE

    def test_anchor_missing_tail_tag(self):
        """A3: a genuinely missing tail replaces head->EOF with a distinct tag."""
        content = "First sentence. Middle content. Last sentence.\n"
        new_content, tag = anchor_replace_with_tag(
            content, "First sentence.", "Nonexistent tail.", "Replacement."
        )
        assert new_content is not None
        assert tag == FallbackTag.ANCHOR_MISSING_TAIL


class TestEditLog:
    """JSONL logging is structured and crash-safe."""

    def test_log_writes_required_fields(self, tmp_path):
        log_path = tmp_path / "edit_log.jsonl"
        edit_log = EditLog(path=log_path)
        edit_log.log("/some/path/main.tex", "gpt-4", "applied", FallbackTag.PERFECT)

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert set(record.keys()) == {
            "timestamp",
            "basename",
            "document_type",
            "model",
            "outcome",
            "fallback",
        }
        assert record["basename"] == "main.tex"
        assert record["document_type"] == "latex"
        assert record["model"] == "gpt-4"
        assert record["outcome"] == "applied"
        assert record["fallback"] == "perfect"
        assert "T" in record["timestamp"]

    def test_log_detects_unknown_document_type(self, tmp_path):
        log_path = tmp_path / "edit_log.jsonl"
        edit_log = EditLog(path=log_path)
        edit_log.log("/some/path/unknown.xyz", "gpt-4", "failed", FallbackTag.EDIT_DISTANCE)

        record = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert record["document_type"] == "unknown"

    def test_log_unknown_fallback_defaults_to_edit_distance(self, tmp_path):
        log_path = tmp_path / "edit_log.jsonl"
        edit_log = EditLog(path=log_path)
        edit_log.log("main.tex", "gpt-4", "applied", "not-a-real-tag")

        record = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert record["fallback"] == "edit-distance"

    def test_log_survives_read_only_directory(self, tmp_path):
        log_path = tmp_path / "readonly" / "edit_log.jsonl"
        log_path.parent.mkdir(mode=0o500, exist_ok=True)
        io = MagicMock()
        edit_log = EditLog(io=io, path=log_path)
        edit_log.log("main.tex", "gpt-4", "applied", FallbackTag.PERFECT)
        # Should not raise and should warn via IO.
        assert io.tool_warning.called

    def test_log_survives_missing_parent_directory_without_permission(self, tmp_path):
        # Create a path under a non-existent directory that cannot be created.
        log_path = tmp_path / "missing" / "deep" / "edit_log.jsonl"
        io = MagicMock()
        edit_log = EditLog(io=io, path=log_path)
        # Simulate an error during directory creation.
        original_mkdir = Path.mkdir

        def raise_oserror(*args, **kwargs):
            raise OSError("cannot create directory")

        Path.mkdir = raise_oserror
        try:
            edit_log.log("main.tex", "gpt-4", "applied", FallbackTag.PERFECT)
        finally:
            Path.mkdir = original_mkdir
        assert io.tool_warning.called
