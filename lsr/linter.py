import os
import re
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

from grep_ast import TreeContext

from lsr.dump import dump  # noqa: F401
from lsr.run_cmd import run_cmd_subprocess  # noqa: F401

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)


class Linter:
    def __init__(self, encoding="utf-8", root=None):
        self.encoding = encoding
        self.root = root

        self.languages = dict(
            python=self.py_lint,
            latex=self.latex_lint,
        )

        self.all_lint_cmds = dict()

    def set_linter(self, lang, cmd):
        self.all_lint_cmds[lang] = cmd

    def get_rel_fname(self, fname):
        if self.root:
            return os.path.relpath(fname, self.root)
        return fname

    def run_cmd(self, cmd, rel_fname):
        cmd += [rel_fname]
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding=self.encoding,
                errors="replace",
            )
        except Exception as e:
            print(f"Unable to execute lint command: {cmd}")
            print(e)
            return

        stdout = process.stdout
        if not stdout:
            return

        try:
            lines = list(stdout)
        except Exception:
            return

        if lines:
            res = "".join(lines)
            if res.strip():
                return res

    def run_cmd_with_worktree(self, cmd, rel_fname, cwd):
        try:
            env = os.environ.copy()
            env["GIT_WORK_TREE"] = cwd
            result = subprocess.run(
                cmd + [rel_fname],
                capture_output=True,
                text=True,
                cwd=cwd,
                env=env,
            )
            return result.stdout + result.stderr
        except Exception as e:
            print(f"Error running lint command: {e}")
            return ""

    def lint(self, fname, cmd=None):
        rel_fname = self.get_rel_fname(fname)

        try:
            code = Path(fname).read_text(encoding=self.encoding, errors="replace")
        except Exception:
            return

        res = ""
        for lang, lint_fn in self.languages.items():
            if not cmd or cmd == lang:
                # Skip Python linting for .tex files
                if lang == "python" and fname.endswith(".tex"):
                    continue
                lintres = lint_fn(fname, rel_fname, code)
                if lintres:
                    res += "```"
                    res += lintres.text
                    res += "\n"
                    res += tree_context(rel_fname, code, lintres.lines)

        if not res and cmd:
            # Try to run the command directly
            lintres = self.run_cmd(cmd.split(), rel_fname)
            if lintres:
                res = "```"
                res += lintres
                res += "\n"

        return res

    def py_lint(self, fname, rel_fname, code):
        basic_res = basic_lint(rel_fname, code)
        compile_res = lint_python_compile(fname, code)
        flake_res = self.flake8_lint(rel_fname)

        text = ""
        lines = set()
        for res in [basic_res, compile_res, flake_res]:
            if not res:
                continue
            if text:
                text += "\n"
            text += res.text
            lines.update(res.lines)

        if text or lines:
            return LintResult(text, lines)

    def flake8_lint(self, rel_fname):
        fatal = "E9,F821,F823,F831,F406,F407,F701,F702,F704,F706"
        flake8_cmd = [
            sys.executable,
            "-m",
            "flake8",
            f"--select={fatal}",
            "--show-source",
            "--isolated",
            rel_fname,
        ]

        text = f"## Running: {' '.join(flake8_cmd)}\n\n"

        try:
            result = subprocess.run(
                flake8_cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding=self.encoding,
                errors="replace",
                cwd=self.root,
            )
            errors = result.stdout + result.stderr
        except Exception as e:
            print(f"Error running flake8: {e}")
            return

        if not errors.strip():
            return

        text += errors
        lines = set()
        for line in errors.split("\n"):
            match = re.search(r":(\d+):", line)
            if match:
                lines.add(int(match.group(1)))

        return LintResult(text, lines)

    def latex_lint(self, fname, rel_fname, code):
        """Basic LaTeX syntax checking."""
        text = ""
        lines = set()

        # Check for unclosed environments
        begin_count = len(re.findall(r"\\begin\{", code))
        end_count = len(re.findall(r"\\end\{", code))
        if begin_count != end_count:
            diff = begin_count - end_count
            text += f"Unclosed environments: {diff} more \\begin than \\end\n"
            # Find lines with \\begin
            for i, line in enumerate(code.split("\n"), 1):
                if "\\begin{" in line:
                    lines.add(i)

        # Check for unclosed braces (simple check)
        brace_count = 0
        for line_num, line in enumerate(code.split("\n"), 1):
            for char in line:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
            if brace_count < 0:
                text += f"Unmatched closing brace on line {line_num}\n"
                lines.add(line_num)
                brace_count = 0

        # Check for undefined references (basic pattern)
        ref_match = re.findall(r"\\ref\{([^}]+)\}", code)
        label_match = set(re.findall(r"\\label\{([^}]+)\}", code))

        # Check if all refs have labels
        for ref in ref_match:
            if ref not in label_match:
                text += f"Undefined reference: \\{{{ref}}}\n"

        if text or lines:
            return LintResult(text, list(lines))


@dataclass
class LintResult:
    text: str
    lines: list


def tree_context(fname, code, lines):
    if not lines:
        return ""

    try:
        context = TreeContext(fname, code)
        context.add_lines_of_interest(lines)
        context.add_context()
        return context.format()
    except Exception:
        return ""


def basic_lint(fname, code):
    """Basic syntax check using compile."""
    try:
        compile(code, fname, "exec")
    except SyntaxError as e:
        if e.lineno:
            return LintResult(
                f"SyntaxError: {e.msg}\nLine: {e.lineno}\n",
                [e.lineno],
            )
    return None


def lint_python_compile(fname, code):
    """Check Python syntax."""
    try:
        compile(code, fname, "exec")
    except SyntaxError as e:
        if e.lineno:
            return LintResult(
                f"Compile error: {e.msg}\nLine: {e.lineno}\n",
                [e.lineno],
            )
    return None
