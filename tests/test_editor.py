"""Tests for lsr/editor.py editor discovery and command handling."""

from unittest.mock import patch

from lsr.editor import discover_graphical_editor


class TestDiscoverGraphicalEditor:
    def test_prefers_code(self):
        with patch("shutil.which", side_effect=lambda cmd: cmd in ("code", "vim")):
            assert discover_graphical_editor() == "code"

    def test_falls_back_to_zed(self):
        with patch("shutil.which", side_effect=lambda cmd: cmd in ("zed", "vim")):
            assert discover_graphical_editor() == "zed"

    def test_returns_none_when_no_editor(self):
        with patch("shutil.which", return_value=None):
            assert discover_graphical_editor() is None
