"""
Tests for latex_tools pure functions: extract_latex_structure, get_latex_packages,
extract_text_environments, find_main_tex_file.
No pdflatex binary required.
"""

from __future__ import annotations

from pathlib import Path

from lsr.latex_tools import (
    TypstCompiler,
    extract_latex_structure,
    extract_text_environments,
    find_main_tex_file,
    find_main_typ_file,
    get_latex_packages,
)


class TestExtractLatexStructure:
    """extract_latex_structure parses LaTeX into sections/subsections/environments/cites."""

    def test_empty_content(self):
        result = extract_latex_structure("")
        assert result == {
            "sections": [],
            "subsections": [],
            "figures": 0,
            "tables": 0,
            "equations": 0,
            "references": [],
        }
        content = r"""
\section{Introduction}
Some text.
\subsection{Background}
More text.
\section{Methods}
We use \cite{smith2020} and \cite{jones2019}.
\begin{figure}
\includegraphics{plot.png}
\end{figure}
\begin{table}
...
\end{table}
\begin{equation}
E = mc^2
\end{equation}
"""
        result = extract_latex_structure(content)
        assert result["sections"] == ["Introduction", "Methods"]
        assert result["subsections"] == ["Background"]
        assert result["figures"] == 1
        assert result["tables"] == 1
        assert result["equations"] == 1
        assert result["references"] == ["smith2020", "jones2019"]

    def test_align_and_gather_counted_as_equations(self):
        content = r"""
\begin{align}
a = b
\end{align}
\begin{gather}
c = d
\end{gather}
"""
        result = extract_latex_structure(content)
        assert result["equations"] == 2

    def test_multiple_figures_and_tables(self):
        content = r"""
\begin{figure}
A
\end{figure}
\begin{figure}
B
\end{figure}
\begin{table}
X
\end{table}
"""
        result = extract_latex_structure(content)
        assert result["figures"] == 2
        assert result["tables"] == 1

    def test_multiple_citations_in_one_cite(self):
        content = r"\cite{key1,key2,key3}"
        result = extract_latex_structure(content)
        assert result["references"] == ["key1,key2,key3"]

    def test_no_subsections(self):
        content = r"\section{Only}"
        result = extract_latex_structure(content)
        assert result["subsections"] == []


class TestGetLatexPackages:
    """get_latex_packages extracts \\usepackage{...} package names."""

    def test_single_package(self):
        assert get_latex_packages(r"\usepackage{graphicx}") == ["graphicx"]

    def test_multiple_packages(self):
        content = r"""
\usepackage{amsmath}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{hyperref}
"""
        result = get_latex_packages(content)
        assert result == ["amsmath", "fontenc", "inputenc", "hyperref"]

    def test_no_packages(self):
        assert get_latex_packages(r"\documentclass{article}") == []

    def test_optional_argument_ignored(self):
        assert get_latex_packages(r"\usepackage[pdfa]{hyperref}") == ["hyperref"]


class TestExtractTextEnvironments:
    """extract_text_environments extracts paragraphs from selected LaTeX items."""

    def test_simple_paragraph(self):
        items = [
            ("section", "Intro", 0, 0, "Hello world.\n\nSecond paragraph."),
        ]
        result = extract_text_environments(items)
        assert len(result) == 2
        assert result[0]["section"] == "Intro"
        assert result[0]["para_id"] == 0
        assert result[0]["text"] == "Hello world."
        assert result[1]["para_id"] == 1
        assert result[1]["text"] == "Second paragraph."

    def test_empty_input(self):
        assert extract_text_environments([]) == []

    def test_skips_figure_and_verbatim(self):
        items = [
            (
                "section",
                "S",
                0,
                0,
                "Before.\n\\begin{figure}\nhidden\n\\end{figure}\n"
                "\\begin{verbatim}\nskip\n\\end{verbatim}\nAfter.",
            ),
        ]
        result = extract_text_environments(items)
        texts = [p["text"] for p in result]
        assert any("Before" in t for t in texts)
        assert any("After" in t for t in texts)
        assert not any("hidden" in t for t in texts)
        assert not any("skip" in t for t in texts)

    def test_multiple_sections(self):
        items = [
            ("section", "Intro", 0, 0, "Para A."),
            ("section", "Methods", 0, 0, "Para B."),
        ]
        result = extract_text_environments(items)
        assert len(result) == 2
        assert result[0]["section"] == "Intro"
        assert result[1]["section"] == "Methods"


class TestFindMainTexFile:
    """find_main_tex_file locates the main .tex by name or \\documentclass."""

    def test_main_tex(self, tmp_path: Path):
        (tmp_path / "main.tex").write_text(r"\documentclass{article}")
        assert find_main_tex_file(str(tmp_path)) == str(tmp_path / "main.tex")

    def test_paper_tex(self, tmp_path: Path):
        (tmp_path / "paper.tex").write_text(r"\documentclass{article}")
        result = find_main_tex_file(str(tmp_path))
        assert result == str(tmp_path / "paper.tex")

    def test_thesis_tex(self, tmp_path: Path):
        (tmp_path / "thesis.tex").write_text(r"\documentclass{report}")
        result = find_main_tex_file(str(tmp_path))
        assert result == str(tmp_path / "thesis.tex")

    def test_document_tex(self, tmp_path: Path):
        (tmp_path / "document.tex").write_text(r"\documentclass{book}")
        result = find_main_tex_file(str(tmp_path))
        assert result == str(tmp_path / "document.tex")

    def test_documentclass_detection(self, tmp_path: Path):
        (tmp_path / "mypaper.tex").write_text(r"\documentclass{article}")
        result = find_main_tex_file(str(tmp_path))
        assert result == str(tmp_path / "mypaper.tex")

    def test_no_tex_files_returns_none(self, tmp_path: Path):
        assert find_main_tex_file(str(tmp_path)) is None

    def test_tex_without_documentclass_skipped(self, tmp_path: Path):
        (tmp_path / "chunk.tex").write_text(r"\section{Intro}")
        assert find_main_tex_file(str(tmp_path)) is None

    def test_named_candidate_takes_priority(self, tmp_path: Path):
        # main.tex wins over documentclass detection
        (tmp_path / "main.tex").write_text("no documentclass")
        (tmp_path / "other.tex").write_text(r"\documentclass{article}")
        result = find_main_tex_file(str(tmp_path))
        assert result == str(tmp_path / "main.tex")


class TestFindMainTypFile:
    """find_main_typ_file locates the main .typ by name or first match."""

    def test_main_typ(self, tmp_path: Path):
        (tmp_path / "main.typ").write_text("= Introduction")
        assert find_main_typ_file(str(tmp_path)) == str(tmp_path / "main.typ")

    def test_paper_typ(self, tmp_path: Path):
        (tmp_path / "paper.typ").write_text("= Introduction")
        result = find_main_typ_file(str(tmp_path))
        assert result == str(tmp_path / "paper.typ")

    def test_first_typ_fallback(self, tmp_path: Path):
        (tmp_path / "alpha.typ").write_text("= Alpha")
        (tmp_path / "beta.typ").write_text("= Beta")
        result = find_main_typ_file(str(tmp_path))
        assert result == str(tmp_path / "alpha.typ")

    def test_no_typ_files_returns_none(self, tmp_path: Path):
        assert find_main_typ_file(str(tmp_path)) is None


class TestTypstCompilerErrorParsing:
    """TypstCompiler error parsing without requiring the typst binary."""

    def test_parse_errors_extracts_line(self):
        compiler = TypstCompiler.__new__(TypstCompiler)
        output = "error: unknown variable\n" "   ┌─ main.typ:3:5\n"
        errors = compiler._parse_errors(output)
        assert len(errors) == 1
        assert errors[0]["line"] == 3
        assert "unknown variable" in errors[0]["message"]

    def test_parse_errors_no_line(self):
        compiler = TypstCompiler.__new__(TypstCompiler)
        errors = compiler._parse_errors("error: something went wrong")
        assert len(errors) == 1
        assert errors[0]["line"] is None
