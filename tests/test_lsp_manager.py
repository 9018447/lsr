"""Tests for lsr/lsp_manager.py."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from lsr.document_types import LATEX, MARKDOWN, TYPST
from lsr.lsp_manager import LspManager


class TestSymbolsToSections:
    def test_markdown_symbols_include_body(self):
        """Markdown sections parsed via LSP helper must include body text."""
        content = "# Title\n\nIntro body.\n\n## Section 1\n\nSection body.\n"
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name

        try:
            items = LspManager._symbols_to_sections(path, [], MARKDOWN)
        finally:
            Path(path).unlink()

        assert len(items) == 2
        assert items[0][0] == "section"
        assert items[0][1] == "Title"
        assert "Intro body." in items[0][4]
        assert items[1][0] == "subsection"
        assert items[1][1] == "Section 1"
        assert "Section body." in items[1][4]

    def test_typst_symbols_include_body(self):
        """Typst sections parsed via LSP helper must include body text."""
        content = "= Title\n\nIntro body.\n\n== Section 1\n\nSection body.\n"
        with tempfile.NamedTemporaryFile("w", suffix=".typ", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name

        try:
            items = LspManager._symbols_to_sections(path, [], TYPST)
        finally:
            Path(path).unlink()

        assert len(items) == 2
        assert items[0][0] == "section"
        assert items[0][1] == "Title"
        assert "Intro body." in items[0][4]
        assert items[1][0] == "subsection"
        assert items[1][1] == "Section 1"
        assert "Section body." in items[1][4]


class TestLspManagerOverrides:
    def test_server_override_used(self):
        manager = LspManager(
            workspace_root="/tmp",
            server_overrides={"latex": "/opt/texlab"},
        )

        client = MagicMock()
        with patch("lsr.lsp_manager.LspClient", return_value=client):
            with patch("shutil.which", return_value="/opt/texlab"):
                result = manager._get_client(LATEX)

        assert result is client
        client.start.assert_called_once()
        call_kwargs = client.start.call_args.kwargs
        assert call_kwargs["command"] == "/opt/texlab"

    def test_disabled_manager_returns_none(self):
        manager = LspManager(workspace_root="/tmp", enabled=False)
        assert manager._get_client(LATEX) is None
        assert manager.get_symbols("/tmp/main.tex") is None
