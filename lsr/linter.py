import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class Linter:
    def __init__(self, encoding="utf-8", root=None):
        self.encoding = encoding
        self.root = root

        self.languages = dict(
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
    """Show a few lines of context around each reported line."""
    if not lines:
        return ""

    line_list = code.splitlines()
    line_set = set(lines)
    output = [f"{fname}:"]
    shown = set()

    for ln in sorted(line_set):
        if ln < 1 or ln > len(line_list):
            continue
        start = max(ln - 2, 1)
        end = min(ln + 2, len(line_list))
        for i in range(start, end + 1):
            if i in shown:
                continue
            shown.add(i)
            prefix = ">>> " if i in line_set else "    "
            output.append(f"{prefix}{i:4d}: {line_list[i - 1]}")

    if len(output) == 1:
        return ""
    return "\n".join(output) + "\n"



