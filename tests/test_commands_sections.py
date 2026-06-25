"""Tests for document-type-aware section editing in lsr/commands.py."""

import json
import os
from unittest.mock import MagicMock

from lsr.commands import Commands


def make_commands(tmp_path):
    io = MagicMock()
    io.tool_output = MagicMock()
    io.tool_error = MagicMock()

    coder = MagicMock()
    coder.root = str(tmp_path)
    coder.abs_root_path = lambda p: os.path.join(str(tmp_path), p)
    coder.get_rel_fname = lambda p: os.path.relpath(p, str(tmp_path))
    coder.abs_fnames = set()
    coder.abs_read_only_fnames = set()
    coder.repo = None

    args = MagicMock()
    args.disable_lsp = True
    args.lsp_server_latex = "texlab"
    args.lsp_server_typst = "tinymist"
    args.lsp_server_markdown = "marksman"

    commands = Commands(io, coder, args=args)
    return commands


class TestFindDocumentFiles:
    def test_finds_all_manuscript_extensions(self, tmp_path):
        work = tmp_path / "work"
        work.mkdir()
        commands = make_commands(work)
        (work / "main.tex").write_text("x")
        (work / "main.typ").write_text("x")
        (work / "README.md").write_text("x")

        files = commands._find_document_files()
        assert sorted(files) == ["README.md", "main.tex", "main.typ"]

    def test_filters_by_extension(self, tmp_path):
        work = tmp_path / "work"
        work.mkdir()
        commands = make_commands(work)
        (work / "main.tex").write_text("x")
        (work / "main.typ").write_text("x")

        files = commands._find_document_files({".tex"})
        assert files == ["main.tex"]


class TestMergeSectionsFromSession:
    def test_merge_markdown_sections(self, tmp_path):
        commands = make_commands(tmp_path)

        original = tmp_path / "paper.md"
        original.write_text("""# Introduction

Intro text.

# Methods

Methods text.
""")

        tmp_file = tmp_path / "lsr_edit_introduction_methods_abc12345.md"
        tmp_file.write_text("""<!-- === LSR: Edit File (hash: header) === -->
<!-- === LSR: Edit the sections below, then run /edit-done (hash: instructions) === -->

<!-- === section: Introduction (hash: abcdef12) === -->
# Introduction

Updated intro text.

<!-- === section: Methods (hash: 34567890) === -->
# Methods

Updated methods text.
""")

        session_file = str(tmp_file) + ".session"
        session = {
            "original_file": str(original),
            "sections": [
                {
                    "hash": "abcdef12",
                    "type": "section",
                    "title": "Introduction",
                    "start_line": 0,
                    "end_line": 2,
                    "original_content": "# Introduction\n\nIntro text.",
                },
                {
                    "hash": "34567890",
                    "type": "section",
                    "title": "Methods",
                    "start_line": 4,
                    "end_line": 6,
                    "original_content": "# Methods\n\nMethods text.",
                },
            ],
        }
        with open(session_file, "w") as f:
            json.dump(session, f)

        commands._merge_sections_from_session(session_file)

        result = original.read_text()
        assert "Updated intro text." in result
        assert "Updated methods text." in result
        assert "Intro text." not in result
        assert "Methods text." not in result

    def test_merge_typst_sections(self, tmp_path):
        commands = make_commands(tmp_path)

        original = tmp_path / "paper.typ"
        original.write_text("""= Introduction

Intro text.

= Methods

Methods text.
""")

        tmp_file = tmp_path / "lsr_edit_introduction_methods_abc12345.typ"
        tmp_file.write_text("""// === LSR: Edit File (hash: header) ===
// === LSR: Edit the sections below, then run /edit-done (hash: instructions) ===

// === section: Introduction (hash: abcdef12) ===
= Introduction

Updated intro text.

// === section: Methods (hash: 34567890) ===
= Methods

Updated methods text.
""")

        session_file = str(tmp_file) + ".session"
        session = {
            "original_file": str(original),
            "sections": [
                {
                    "hash": "abcdef12",
                    "type": "section",
                    "title": "Introduction",
                    "start_line": 0,
                    "end_line": 2,
                    "original_content": "= Introduction\n\nIntro text.",
                },
                {
                    "hash": "34567890",
                    "type": "section",
                    "title": "Methods",
                    "start_line": 4,
                    "end_line": 6,
                    "original_content": "= Methods\n\nMethods text.",
                },
            ],
        }
        with open(session_file, "w") as f:
            json.dump(session, f)

        commands._merge_sections_from_session(session_file)

        result = original.read_text()
        assert "Updated intro text." in result
        assert "Updated methods text." in result
        assert "Intro text." not in result
        assert "Methods text." not in result


class TestExtractParagraphsFromTemp:
    def test_extracts_markdown_paragraphs(self, tmp_path):
        commands = make_commands(tmp_path)
        content = """<!-- === LSR: Edit File (hash: header) === -->
<!-- === LSR: Edit the sections below, then run /edit-done (hash: instructions) === -->

<!-- === section: Introduction (hash: abcdef12) === -->
# Introduction

Intro paragraph.

<!-- === section: Methods (hash: 34567890) === -->
## Methods

Methods paragraph.
"""
        paragraphs = commands._extract_paragraphs_from_temp(content)
        assert len(paragraphs) == 4
        assert paragraphs[0]["section"] == "Introduction"
        assert "# Introduction" in paragraphs[0]["text"]
        assert paragraphs[1]["section"] == "Introduction"
        assert "Intro paragraph." in paragraphs[1]["text"]
        assert paragraphs[2]["section"] == "Methods"
        assert "## Methods" in paragraphs[2]["text"]
        assert paragraphs[3]["section"] == "Methods"
        assert "Methods paragraph." in paragraphs[3]["text"]
