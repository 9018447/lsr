#!/usr/bin/env python
"""LaTeX compilation and tool integration for the research assistant."""

import os
import re
import subprocess
from pathlib import Path


class LatexCompiler:
    """Handles LaTeX compilation with error parsing."""

    ENGINES = {
        "pdflatex": "pdflatex",
        "xelatex": "xelatex",
        "lualatex": "lualatex",
    }

    def __init__(self, engine="pdflatex", root=None):
        self.engine = engine
        self.root = root or os.getcwd()
        self._validate_engine()

    def _validate_engine(self):
        """Check if the LaTeX engine is available."""
        import shutil

        if not shutil.which(self.ENGINES.get(self.engine, self.engine)):
            raise RuntimeError(
                f"LaTeX engine '{self.engine}' not found. "
                f"Please install a TeX distribution (e.g., TeX Live, MiKTeX)."
            )

    def compile(self, tex_file, extra_args=None):
        """
        Compile a .tex file.

        Returns:
            tuple: (success: bool, output: str, errors: list)
        """
        abs_path = os.path.abspath(tex_file)
        working_dir = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)

        cmd = [self.ENGINES.get(self.engine, self.engine)]
        cmd.extend(["-interaction=nonstopmode", "-halt-on-error"])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(filename)

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            output = result.stdout + result.stderr
            errors = self._parse_errors(output)

            return result.returncode == 0, output, errors

        except subprocess.TimeoutExpired:
            return False, "Compilation timed out after 120 seconds.", []
        except Exception as e:
            return False, str(e), []

    def _parse_errors(self, output):
        """Parse LaTeX compilation output for errors."""
        errors = []
        lines = output.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for error patterns
            if line.startswith("!") or "error" in line.lower():
                error = {
                    "line": None,
                    "message": line,
                    "file": None,
                }

                # Try to extract line number
                line_match = re.search(r"l\.(\d+)", line)
                if line_match:
                    error["line"] = int(line_match.group(1))

                # Look for file reference
                file_match = re.search(r"\(([^)]+\.tex)", line)
                if file_match:
                    error["file"] = file_match.group(1)

                errors.append(error)

            i += 1

        return errors

    def run_bibtex(self, aux_file):
        """Run BibTeX on an .aux file."""
        working_dir = os.path.dirname(os.path.abspath(aux_file))
        filename = os.path.basename(aux_file)

        try:
            result = subprocess.run(
                ["bibtex", filename],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)


def find_main_tex_file(root=None):
    """Find the main .tex file in a project."""
    root = root or os.getcwd()

    # Look for common main file names
    candidates = ["main.tex", "paper.tex", "thesis.tex", "document.tex"]

    for candidate in candidates:
        path = os.path.join(root, candidate)
        if os.path.exists(path):
            return path

    # Look for any .tex file with \documentclass
    for tex_file in Path(root).glob("*.tex"):
        try:
            with open(tex_file, "r", encoding="utf-8") as f:
                content = f.read(1000)  # Read first 1000 chars
                if "\\documentclass" in content:
                    return str(tex_file)
        except Exception:
            continue

    return None


def extract_latex_structure(content):
    """
    Extract structure from LaTeX content.

    Returns:
        dict with sections, figures, tables, equations, references
    """
    structure = {
        "sections": [],
        "subsections": [],
        "figures": [],
        "tables": [],
        "equations": [],
        "references": [],
    }

    # Extract sections
    structure["sections"] = re.findall(r"\\section\{([^}]+)\}", content)
    structure["subsections"] = re.findall(r"\\subsection\{([^}]+)\}", content)

    # Count environments
    structure["figures"] = len(re.findall(r"\\begin\{figure\}", content))
    structure["tables"] = len(re.findall(r"\\begin\{table\}", content))
    structure["equations"] = len(
        re.findall(r"\\begin\{(equation|align|gather)\}", content)
    )

    # Extract citations
    structure["references"] = re.findall(r"\\cite\{([^}]+)\}", content)

    return structure


def get_latex_packages(content):
    """Extract used packages from LaTeX content."""
    return re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", content)


def extract_text_environments(selected_items):
    """Extract text environments from selected LaTeX sections.

    Args:
        selected_items: list of (type, title, start_line, end_line, content) tuples

    Returns:
        list of dicts with keys: section, para_id, text
        Each dict represents a paragraph of text content.
        Math formulas ($...$, $$...$$, \\begin{equation}...) are preserved for MathJax rendering.
    """
    # Environments to skip (non-text)
    skip_envs = {"figure", "verbatim", "lstlisting", "minted", "code"}

    paragraphs = []

    for item_type, title, start, end, content in selected_items:
        para_id = 0

        # Split content into lines and process
        lines = content.split("\n")
        current_para = []
        in_skip_env = False
        skip_depth = 0
        in_table = False
        table_lines = []
        table_depth = 0

        for line in lines:
            stripped = line.strip()

            # Track skip environments
            for env in skip_envs:
                if re.search(r"\\begin\{" + re.escape(env) + r"\}", stripped):
                    in_skip_env = True
                    skip_depth += 1
                    break
                if re.search(r"\\end\{" + re.escape(env) + r"\}", stripped):
                    skip_depth -= 1
                    if skip_depth <= 0:
                        in_skip_env = False
                        skip_depth = 0
                    break

            if in_skip_env:
                continue

            # Track table environments
            if re.search(r"\\begin\{table\}", stripped):
                in_table = True
                table_lines = []
                table_depth = 1
                # Flush current paragraph
                if current_para:
                    text = "\n".join(current_para)
                    text = _simplify_latex_commands(text)
                    if text.strip():
                        paragraphs.append({
                            "section": title,
                            "para_id": para_id,
                            "text": text,
                        })
                        para_id += 1
                    current_para = []
                continue

            if in_table:
                if re.search(r"\\begin\{table\}", stripped):
                    table_depth += 1
                if re.search(r"\\end\{table\}", stripped):
                    table_depth -= 1
                    if table_depth <= 0:
                        in_table = False
                        # Convert collected table to HTML
                        table_html = _convert_tabular_to_html("\n".join(table_lines))
                        if table_html:
                            paragraphs.append({
                                "section": title,
                                "para_id": para_id,
                                "text": table_html,
                            })
                            para_id += 1
                        table_lines = []
                    continue
                table_lines.append(line)
                continue

            # Skip comments
            if stripped.startswith("%"):
                continue

            # Empty line = paragraph boundary
            if not stripped:
                if current_para:
                    text = "\n".join(current_para)
                    text = _simplify_latex_commands(text)
                    if text.strip():
                        paragraphs.append({
                            "section": title,
                            "para_id": para_id,
                            "text": text,
                        })
                        para_id += 1
                    current_para = []
                continue

            current_para.append(line)

        # Last paragraph
        if current_para:
            text = "\n".join(current_para)
            text = _simplify_latex_commands(text)
            if text.strip():
                paragraphs.append({
                    "section": title,
                    "para_id": para_id,
                    "text": text,
                })

    return paragraphs


def _simplify_latex_commands(text):
    """Simplify LaTeX commands to HTML equivalents.

    Preserves math formulas for MathJax rendering.
    """
    # Convert common formatting commands to HTML
    text = re.sub(r"\\textbf\{([^}]*)\}", r"<b>\1</b>", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"<i>\1</i>", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"<i>\1</i>", text)
    text = re.sub(r"\\underline\{([^}]*)\}", r"<u>\1</u>", text)

    # Remove labels and refs (keep content)
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    text = re.sub(r"\\ref\{([^}]*)\}", r"[\1]", text)
    text = re.sub(r"\\eqref\{([^}]*)\}", r"(\1)", text)
    text = re.sub(r"\\cite\{([^}]*)\}", r"[\1]", text)

    # Remove common non-content commands
    text = re.sub(r"\\noindent", "", text)
    text = re.sub(r"\\vspace\{[^}]*\}", "", text)
    text = re.sub(r"\\hspace\{[^}]*\}", "", text)

    # Clean up extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _convert_tabular_to_html(table_content):
    """Convert LaTeX tabular environment to HTML table.

    Handles basic \\begin{tabular}{...} ... \\end{tabular} syntax.
    """
    # Extract tabular content
    tabular_match = re.search(
        r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}",
        table_content,
        re.DOTALL
    )
    if not tabular_match:
        return None

    col_spec = tabular_match.group(1)
    body = tabular_match.group(2).strip()

    # Extract caption if present
    caption_match = re.search(r"\\caption\{([^}]*)\}", table_content)
    caption = caption_match.group(1) if caption_match else None

    # Parse rows
    rows = []
    for row_text in body.split("\\\\"):
        row_text = row_text.strip()
        if not row_text or row_text == "\\hline":
            continue
        # Remove \hline
        row_text = re.sub(r"\\hline", "", row_text).strip()
        if not row_text:
            continue
        # Split by & (but not \&)
        cells = re.split(r"(?<!\\)&", row_text)
        cells = [c.strip() for c in cells]
        rows.append(cells)

    if not rows:
        return None

    # Build HTML table
    html_parts = ['<table style="border-collapse: collapse; width: 100%; margin: 12pt 0;">']

    if caption:
        html_parts.append(f'<caption style="font-style: italic; margin-bottom: 6pt; color: #504e49;">{_simplify_latex_commands(caption)}</caption>')

    # First row as header
    html_parts.append("<thead><tr>")
    for cell in rows[0]:
        cell_html = _simplify_latex_commands(cell)
        html_parts.append(f'<th style="border: 1px solid #e8e6dc; padding: 6pt 8pt; background: #f5f4ed; text-align: left;">{cell_html}</th>')
    html_parts.append("</tr></thead>")

    # Remaining rows as body
    html_parts.append("<tbody>")
    for row in rows[1:]:
        html_parts.append("<tr>")
        for cell in row:
            cell_html = _simplify_latex_commands(cell)
            html_parts.append(f'<td style="border: 1px solid #e8e6dc; padding: 6pt 8pt;">{cell_html}</td>')
        html_parts.append("</tr>")
    html_parts.append("</tbody>")

    html_parts.append("</table>")
    return "\n".join(html_parts)
