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
