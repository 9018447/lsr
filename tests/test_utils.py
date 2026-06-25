"""
Tests for lsr/utils.py — format_tokens, is_image_file, safe_abs_path, find_common_root.
"""

import os
from pathlib import Path

import pytest

from lsr.utils import (
    find_common_root,
    format_tokens,
    is_image_file,
    read_text_robust,
    safe_abs_path,
)


class TestFormatTokens:
    """Tests for format_tokens(count)."""

    @pytest.mark.parametrize(
        "count,expected",
        [
            (0, "0"),
            (1, "1"),
            (500, "500"),
            (999, "999"),
            (1000, "1.0k"),
            (1500, "1.5k"),
            (9900, "9.9k"),
            (9999, "10.0k"),
            (10000, "10k"),
            (25000, "25k"),
            (100000, "100k"),
        ],
    )
    def test_format_tokens(self, count, expected):
        assert format_tokens(count) == expected


class TestIsImageFile:
    """Tests for is_image_file(name)."""

    @pytest.mark.parametrize(
        "name",
        [
            "photo.png",
            "photo.jpg",
            "photo.jpeg",
            "photo.gif",
            "photo.webp",
            "photo.bmp",
            "photo.tiff",
            "photo.pdf",
            # Path objects
        ],
    )
    def test_image_extensions(self, name):
        """Files with known image extensions are recognised."""
        assert is_image_file(name) is True

    def test_path_object(self):
        """A Path object is handled (converted to str)."""
        assert is_image_file(Path("photo.png")) is True

    @pytest.mark.parametrize(
        "name",
        [
            "document.txt",
            "main.tex",
            "script.py",
            "styles.css",
            "data.json",
            "no_extension",
            "photo.png.txt",
        ],
    )
    def test_non_image(self, name):
        """Files without known image extensions return False."""
        assert is_image_file(name) is False


class TestSafeAbsPath:
    """Tests for safe_abs_path(res)."""

    def test_relative_path(self):
        """A relative path is resolved to an absolute path."""
        result = safe_abs_path("some/relative/path")
        assert os.path.isabs(result)
        assert result.endswith("some/relative/path")

    def test_absolute_path(self):
        """An absolute path is normalised (resolved)."""
        result = safe_abs_path("/tmp/../tmp/test_file")
        assert result == "/tmp/test_file"

    def test_non_existent_path(self):
        """A path that does not exist does not raise and returns an absolute path."""
        result = safe_abs_path("/nonexistent_dir_xyz/file.txt")
        assert os.path.isabs(result)
        assert "nonexistent_dir_xyz" in result


class TestFindCommonRoot:
    """Tests for find_common_root(abs_fnames)."""

    def test_single_file(self, tmp_path):
        """A single file returns its directory."""
        d = tmp_path / "sub"
        d.mkdir()
        f = d / "file.txt"
        f.write_text("")
        result = find_common_root([str(f)])
        assert result == safe_abs_path(str(d))

    def test_two_files_same_dir(self, tmp_path):
        """Two files in the same directory return that directory."""
        d = tmp_path / "shared"
        d.mkdir()
        a = d / "a.txt"
        b = d / "b.txt"
        a.write_text("")
        b.write_text("")
        result = find_common_root([str(a), str(b)])
        assert result == safe_abs_path(str(d))

    def test_two_files_different_dirs(self, tmp_path):
        """Two files in sibling directories return the common parent."""
        base = tmp_path / "parent"
        d1 = base / "alpha"
        d2 = base / "beta"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        a = d1 / "a.txt"
        b = d2 / "b.txt"
        a.write_text("")
        b.write_text("")
        result = find_common_root([str(a), str(b)])
        assert result == safe_abs_path(str(base))

    def test_empty_set(self):
        """Empty set falls back to the current working directory."""
        result = find_common_root(set())
        assert result == safe_abs_path(os.getcwd())


class TestReadTextRobust:
    """Tests for read_text_robust(path)."""

    def test_reads_utf8(self, tmp_path):
        f = tmp_path / "utf8.txt"
        f.write_text("hello 世界", encoding="utf-8")
        assert read_text_robust(str(f)) == "hello 世界"

    def test_reads_utf8_with_bom(self, tmp_path):
        f = tmp_path / "bom.txt"
        f.write_bytes(b"\xef\xbb\xbfhello")
        assert read_text_robust(str(f)) == "hello"

    def test_reads_latin1_on_invalid_utf8(self, tmp_path):
        f = tmp_path / "latin1.txt"
        f.write_bytes(b"caf\xe9")
        assert read_text_robust(str(f)) == "café"

    def test_returns_none_for_missing_file(self, tmp_path):
        f = tmp_path / "missing.txt"
        assert read_text_robust(str(f)) is None
