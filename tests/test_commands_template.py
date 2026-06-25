"""Tests for the /template command in lsr/commands.py."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from prompt_toolkit.document import Document

from lsr.commands import Commands


def make_commands(tmp_path, template_dir=None):
    io = MagicMock()
    io.tool_output = MagicMock()
    io.tool_error = MagicMock()

    coder = MagicMock()
    coder.root = str(tmp_path)
    coder.use_cwd = True

    args = MagicMock()

    commands = Commands(io, coder, args=args)
    if template_dir:
        commands._template_search_paths = [Path(template_dir)]
    return commands


class TestCmdTemplate:
    def test_no_args_lists_templates(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        commands = make_commands(tmp_path)
        commands.cmd_template("")

        output = "\n".join(call.args[0] for call in commands.io.tool_output.call_args_list)
        assert "Available templates:" in output
        assert "article" in output
        assert "Usage:" in output

    def test_filename_first_argument_uses_default_template(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        commands = make_commands(tmp_path)
        commands.cmd_template("main_manuscript.tex")

        assert (tmp_path / "main_manuscript.tex").exists()
        content = (tmp_path / "main_manuscript.tex").read_text()
        assert "\\documentclass" in content
        commands.io.tool_error.assert_not_called()

    def test_template_name_creates_default_filename(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        commands = make_commands(tmp_path)
        commands.cmd_template("article")

        assert (tmp_path / "main.tex").exists()
        content = (tmp_path / "main.tex").read_text()
        assert "\\documentclass{article}" in content

    def test_unknown_template_errors_and_lists_available(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        commands = make_commands(tmp_path)
        commands.cmd_template("nonexistent")

        commands.io.tool_error.assert_called_once()
        error_msg = commands.io.tool_error.call_args[0][0]
        assert "Unknown template: nonexistent" in error_msg

        output = "\n".join(call.args[0] for call in commands.io.tool_output.call_args_list)
        assert "Available templates:" in output or "article" in output

    def test_discovers_template_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        template_dir = tmp_path / "template" / "wiley"
        template_dir.mkdir(parents=True)
        (template_dir / "main_manuscript.tex").write_text(
            "\\documentclass{wiley}\n\\begin{document}\n\\end{document}"
        )

        commands = make_commands(tmp_path)
        commands.cmd_template("wiley output.tex")

        assert (tmp_path / "output.tex").exists()
        content = (tmp_path / "output.tex").read_text()
        assert "\\documentclass{wiley}" in content


class TestCompletionsRawTemplate:
    @pytest.fixture
    def commands(self, tmp_path):
        template_dir = tmp_path / "template" / "wiley"
        template_dir.mkdir(parents=True)
        (template_dir / "main_manuscript.tex").write_text("x")
        return make_commands(tmp_path)

    def _complete(self, commands, text):
        document = Document(text, cursor_position=len(text))
        return list(commands.completions_raw_template(document, MagicMock()))

    def test_empty_first_arg_lists_templates(self, commands):
        completions = self._complete(commands, "/template ")
        texts = [c.text for c in completions]
        assert "wiley" in texts
        assert "article" in texts

    def test_partial_first_arg_filters_templates(self, commands):
        completions = self._complete(commands, "/template w")
        texts = [c.text for c in completions]
        assert texts == ["wiley"]

    def test_second_arg_completes_manuscript_files(self, tmp_path, commands):
        (tmp_path / "main.tex").write_text("x")
        (tmp_path / "notes.txt").write_text("x")

        completions = self._complete(commands, "/template wiley m")
        texts = [c.text for c in completions]
        assert "main.tex" in texts
        assert "notes.txt" not in texts

    def test_filename_as_first_arg_completes_paths(self, tmp_path, commands):
        (tmp_path / "main_manuscript.tex").write_text("x")

        completions = self._complete(commands, "/template main_manuscript.")
        texts = [c.text for c in completions]
        assert "main_manuscript.tex" in texts
