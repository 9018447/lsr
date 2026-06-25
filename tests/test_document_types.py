import os

import pytest

from lsr.document_types import (
    LATEX,
    MARKDOWN,
    TYPST,
    find_main_document,
    get_document_type,
)


class TestDocumentTypeDetection:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("main.tex", LATEX),
            ("paper.bib", LATEX),
            ("thesis.cls", LATEX),
            ("README.md", MARKDOWN),
            ("main.typ", TYPST),
            ("main.txt", None),
            ("Makefile", None),
        ],
    )
    def test_get_document_type(self, path, expected):
        assert get_document_type(path) is expected


class TestLaTeXSections:
    def test_parse_sections(self):
        content = """\\documentclass{article}
\\begin{document}
\\section{Introduction}
Intro text.

\\subsection{Background}
Background text.

\\subsubsection{Motivation}
Motivation text.

\\section{Methods}
Methods text.
"""
        sections = LATEX.parse_sections(content)
        assert len(sections) == 4
        names = [(level, title) for level, title, *_ in sections]
        assert names == [
            ("section", "Introduction"),
            ("subsection", "Background"),
            ("subsubsection", "Motivation"),
            ("section", "Methods"),
        ]

    def test_hash_marker(self):
        marker = LATEX.make_hash_marker("section", "Introduction", "abc123")
        assert marker == "% === section: Introduction (hash: abc123) ==="
        match = LATEX.hash_marker_pattern.search(marker)
        assert match is not None
        assert match.group(1) == "Introduction"
        assert match.group(2) == "abc123"


class TestMarkdownSections:
    def test_parse_sections(self):
        content = """# Introduction

Intro text.

## Background

Background text.

### Motivation

Motivation text.

# Methods

Methods text.
"""
        sections = MARKDOWN.parse_sections(content)
        assert len(sections) == 4
        names = [(level, title) for level, title, *_ in sections]
        assert names == [
            ("section", "Introduction"),
            ("subsection", "Background"),
            ("subsubsection", "Motivation"),
            ("section", "Methods"),
        ]

    def test_hash_marker(self):
        marker = MARKDOWN.make_hash_marker("section", "Introduction", "abc123")
        assert marker == "<!-- === section: Introduction (hash: abc123) === -->"
        match = MARKDOWN.hash_marker_pattern.search(marker)
        assert match is not None
        assert match.group(1) == "Introduction"
        assert match.group(2) == "abc123"


class TestTypstSections:
    def test_parse_sections(self):
        content = """= Introduction

Intro text.

== Background

Background text.

=== Motivation

Motivation text.

= Methods

Methods text.
"""
        sections = TYPST.parse_sections(content)
        assert len(sections) == 4
        names = [(level, title) for level, title, *_ in sections]
        assert names == [
            ("section", "Introduction"),
            ("subsection", "Background"),
            ("subsubsection", "Motivation"),
            ("section", "Methods"),
        ]

    def test_hash_marker(self):
        marker = TYPST.make_hash_marker("section", "Introduction", "abc123")
        assert marker == "// === section: Introduction (hash: abc123) ==="
        match = TYPST.hash_marker_pattern.search(marker)
        assert match is not None
        assert match.group(1) == "Introduction"
        assert match.group(2) == "abc123"


class TestFindMainDocument:
    def test_finds_important_file(self, tmp_path):
        (tmp_path / "main.typ").write_text("= Hello")
        (tmp_path / "other.typ").write_text("= Other")
        found = find_main_document(str(tmp_path), TYPST)
        assert found == os.path.join(str(tmp_path), "main.typ")

    def test_fallback_to_first_matching_extension(self, tmp_path):
        (tmp_path / "alpha.md").write_text("# Alpha")
        (tmp_path / "beta.md").write_text("# Beta")
        found = find_main_document(str(tmp_path), MARKDOWN)
        assert found == os.path.join(str(tmp_path), "alpha.md")

    def test_returns_none_when_no_match(self, tmp_path):
        assert find_main_document(str(tmp_path), TYPST) is None
