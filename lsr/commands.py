import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from os.path import expanduser
from pathlib import Path

import pyperclip
from PIL import Image, ImageGrab
from prompt_toolkit.completion import Completion, PathCompleter
from prompt_toolkit.document import Document

from lsr import models, prompts
from lsr.editor import pipe_editor

from lsr.format_settings import format_settings
from lsr.help import Help, install_help_extra
from lsr.io import CommandCompletionException
from lsr.llm import litellm
from lsr.repo import ANY_GIT_ERROR
from lsr.run_cmd import run_cmd
from lsr.utils import is_image_file

from .dump import dump  # noqa: F401


class SwitchCoder(Exception):
    def __init__(self, placeholder=None, **kwargs):
        self.kwargs = kwargs
        self.placeholder = placeholder


class Commands:
    def clone(self):
        return Commands(
            self.io,
            None,
            verify_ssl=self.verify_ssl,
            args=self.args,
            parser=self.parser,
            verbose=self.verbose,
            editor=self.editor,
            original_read_only_fnames=self.original_read_only_fnames,
        )

    def __init__(
        self,
        io,
        coder,
        verify_ssl=True,
        args=None,
        parser=None,
        verbose=False,
        editor=None,
        original_read_only_fnames=None,
    ):
        self.io = io
        self.coder = coder
        self.parser = parser
        self.args = args
        self.verbose = verbose

        self.verify_ssl = verify_ssl

        self.help = None
        self.editor = editor

        # Store the original read-only filenames provided via args.read
        self.original_read_only_fnames = set(original_read_only_fnames or [])

        # Edit session tracking
        self._last_edit_file = None

    def cmd_model(self, args):
        "Switch the Main Model to a new LLM"

        model_name = args.strip()
        if not model_name:
            announcements = "\n".join(self.coder.get_announcements())
            self.io.tool_output(announcements)
            return

        model = models.Model(
            model_name,
            editor_model=self.coder.main_model.editor_model.name,
            weak_model=self.coder.main_model.weak_model.name,
        )
        models.sanity_check_models(self.io, model)

        # Check if the current edit format is the default for the old model
        old_model_edit_format = self.coder.main_model.edit_format
        current_edit_format = self.coder.edit_format

        new_edit_format = current_edit_format
        if current_edit_format == old_model_edit_format:
            # If the user was using the old model's default, switch to the new model's default
            new_edit_format = model.edit_format

        raise SwitchCoder(main_model=model, edit_format=new_edit_format)

    def cmd_chat_mode(self, args):
        "Switch to a new chat mode"

        from lsr import coders

        ef = args.strip()
        valid_formats = OrderedDict(
            sorted(
                (
                    coder.edit_format,
                    coder.__doc__.strip().split("\n")[0]
                    if coder.__doc__
                    else "No description",
                )
                for coder in coders.__all__
                if getattr(coder, "edit_format", None)
            )
        )

        show_formats = OrderedDict(
            [
                ("help", "Get help about using lsr (usage, config, troubleshoot)."),
                (
                    "ask",
                    "Ask questions about your LaTeX documents without making any changes.",
                ),
                (
                    "plan",
                    "Create a structured writing plan for your research paper.",
                ),
                (
                    "code",
                    "Ask for changes to your LaTeX documents (using the best edit format).",
                ),
            ]
        )

        if ef not in valid_formats and ef not in show_formats:
            if ef:
                self.io.tool_error(f'Chat mode "{ef}" should be one of these:\n')
            else:
                self.io.tool_output("Chat mode should be one of these:\n")

            max_format_length = max(len(format) for format in valid_formats.keys())
            for format, description in show_formats.items():
                self.io.tool_output(f"- {format:<{max_format_length}} : {description}")

            self.io.tool_output("\nOr a valid edit format:\n")
            for format, description in valid_formats.items():
                if format not in show_formats:
                    self.io.tool_output(
                        f"- {format:<{max_format_length}} : {description}"
                    )

            return

        summarize_from_coder = True
        edit_format = ef

        if ef == "code":
            edit_format = self.coder.main_model.edit_format
            summarize_from_coder = False
        elif ef in ("ask", "plan"):
            summarize_from_coder = False

        raise SwitchCoder(
            edit_format=edit_format,
            summarize_from_coder=summarize_from_coder,
        )

    def completions_model(self):
        models = litellm.model_cost.keys()
        return models

    def cmd_models(self, args):
        "Search the list of available models"

        args = args.strip()

        if args:
            models.print_matching_models(self.io, args)
        else:
            self.io.tool_output("Please provide a partial model name to search for.")

    def is_command(self, inp):
        return inp[0] in "/!"

    def get_raw_completions(self, cmd):
        assert cmd.startswith("/")
        cmd = cmd[1:]
        cmd = cmd.replace("-", "_")

        raw_completer = getattr(self, f"completions_raw_{cmd}", None)
        return raw_completer

    def get_completions(self, cmd):
        assert cmd.startswith("/")
        cmd = cmd[1:]

        cmd = cmd.replace("-", "_")
        fun = getattr(self, f"completions_{cmd}", None)
        if not fun:
            return
        return sorted(fun())

    def get_commands(self):
        commands = []
        for attr in dir(self):
            if not attr.startswith("cmd_"):
                continue
            cmd = attr[4:]
            cmd = cmd.replace("_", "-")
            commands.append("/" + cmd)

        return commands

    def do_run(self, cmd_name, args):
        cmd_name = cmd_name.replace("-", "_")
        cmd_method_name = f"cmd_{cmd_name}"
        cmd_method = getattr(self, cmd_method_name, None)
        if not cmd_method:
            self.io.tool_output(f"Error: Command {cmd_name} not found.")
            return

        try:
            return cmd_method(args)
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to complete {cmd_name}: {err}")

    def matching_commands(self, inp):
        words = inp.strip().split()
        if not words:
            return

        first_word = words[0]
        rest_inp = inp[len(words[0]) :].strip()

        all_commands = self.get_commands()
        matching_commands = [cmd for cmd in all_commands if cmd.startswith(first_word)]
        return matching_commands, first_word, rest_inp

    def run(self, inp):
        if inp.startswith("!"):
            return self.do_run("run", inp[1:])

        res = self.matching_commands(inp)
        if res is None:
            return
        matching_commands, first_word, rest_inp = res
        if len(matching_commands) == 1:
            command = matching_commands[0][1:]
            return self.do_run(command, rest_inp)
        elif first_word in matching_commands:
            command = first_word[1:]
            return self.do_run(command, rest_inp)
        elif len(matching_commands) > 1:
            self.io.tool_error(f"Ambiguous command: {', '.join(matching_commands)}")
        else:
            self.io.tool_error(f"Invalid command: {first_word}")

    # any method called cmd_xxx becomes a command automatically.
    # each one must take an args param.

    def cmd_commit(self, args=None):
        "Commit edits to the repo made outside the chat (commit message optional)"
        try:
            self.raw_cmd_commit(args)
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to complete commit: {err}")

    def raw_cmd_commit(self, args=None):
        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        if not self.coder.repo.is_dirty():
            self.io.tool_warning("No more changes to commit.")
            return

        commit_message = args.strip() if args else None
        self.coder.repo.commit(message=commit_message, coder=self.coder)

    def cmd_check(self, args="", fnames=None):
        "Check and fix LaTeX syntax in files or all dirty files if none in chat"

        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        if not fnames:
            fnames = self.coder.get_inchat_relative_files()

        # If still no files, get all dirty files in the repo
        if not fnames and self.coder.repo:
            fnames = self.coder.repo.get_dirty_files()

        if not fnames:
            self.io.tool_warning("No dirty files to lint.")
            return

        fnames = [self.coder.abs_root_path(fname) for fname in fnames]

        lint_coder = None
        for fname in fnames:
            try:
                errors = self.coder.linter.lint(fname)
            except FileNotFoundError as err:
                self.io.tool_error(f"Unable to lint {fname}")
                self.io.tool_output(str(err))
                continue

            if not errors:
                continue

            self.io.tool_output(errors)
            if not self.io.confirm_ask(f"Fix lint errors in {fname}?", default="y"):
                continue

            # Commit everything before we start fixing lint errors
            if self.coder.repo.is_dirty() and self.coder.dirty_commits:
                self.cmd_commit("")

            if not lint_coder:
                lint_coder = self.coder.clone(
                    # Clear the chat history, fnames
                    cur_messages=[],
                    done_messages=[],
                    fnames=None,
                )

            lint_coder.add_rel_fname(fname)
            lint_coder.run(errors)
            lint_coder.abs_fnames = set()

        if lint_coder and self.coder.repo.is_dirty() and self.coder.auto_commits:
            self.cmd_commit("")

    def cmd_clear(self, args):
        "Clear the chat history"

        self._clear_chat_history()
        self.io.tool_output("All chat history cleared.")

    def _drop_all_files(self):
        self.coder.abs_fnames = set()

        # When dropping all files, keep those that were originally provided via args.read
        if self.original_read_only_fnames:
            # Keep only the original read-only files
            to_keep = set()
            for abs_fname in self.coder.abs_read_only_fnames:
                rel_fname = self.coder.get_rel_fname(abs_fname)
                if (
                    abs_fname in self.original_read_only_fnames
                    or rel_fname in self.original_read_only_fnames
                ):
                    to_keep.add(abs_fname)
            self.coder.abs_read_only_fnames = to_keep
        else:
            self.coder.abs_read_only_fnames = set()

    def _clear_chat_history(self):
        self.coder.done_messages = []
        self.coder.cur_messages = []

    def cmd_reset(self, args):
        "Drop all files and clear the chat history"
        self._drop_all_files()
        self._clear_chat_history()
        self.io.tool_output("All files dropped and chat history cleared.")

    def cmd_tokens(self, args):
        "Report on the number of tokens used by the current chat context"

        res = []

        self.coder.choose_fence()

        # system messages
        main_sys = self.coder.fmt_system_prompt(self.coder.gpt_prompts.main_system)
        main_sys += "\n" + self.coder.fmt_system_prompt(
            self.coder.gpt_prompts.system_reminder
        )
        msgs = [
            dict(role="system", content=main_sys),
            dict(
                role="system",
                content=self.coder.fmt_system_prompt(
                    self.coder.gpt_prompts.system_reminder
                ),
            ),
        ]

        tokens = self.coder.main_model.token_count(msgs)
        res.append((tokens, "system messages", ""))

        # chat history
        msgs = self.coder.done_messages + self.coder.cur_messages
        if msgs:
            tokens = self.coder.main_model.token_count(msgs)
            res.append((tokens, "chat history", "use /clear to clear"))

        # repo map
        other_files = set(self.coder.get_all_abs_files()) - set(self.coder.abs_fnames)
        if self.coder.repo_map:
            repo_content = self.coder.repo_map.get_repo_map(
                self.coder.abs_fnames, other_files
            )
            if repo_content:
                tokens = self.coder.main_model.token_count(repo_content)
                res.append((tokens, "repository map", "use --map-tokens to resize"))

        fence = "`" * 3

        file_res = []
        # files
        for fname in self.coder.abs_fnames:
            relative_fname = self.coder.get_rel_fname(fname)
            content = self.io.read_text(fname)
            if is_image_file(relative_fname):
                tokens = self.coder.main_model.token_count_for_image(fname)
            else:
                # approximate
                content = f"{relative_fname}\n{fence}\n" + content + "{fence}\n"
                tokens = self.coder.main_model.token_count(content)
            file_res.append((tokens, f"{relative_fname}", "/drop to remove"))

        # read-only files
        for fname in self.coder.abs_read_only_fnames:
            relative_fname = self.coder.get_rel_fname(fname)
            content = self.io.read_text(fname)
            if content is not None and not is_image_file(relative_fname):
                # approximate
                content = f"{relative_fname}\n{fence}\n" + content + "{fence}\n"
                tokens = self.coder.main_model.token_count(content)
                file_res.append(
                    (tokens, f"{relative_fname} (read-only)", "/drop to remove")
                )

        file_res.sort()
        res.extend(file_res)

        self.io.tool_output(
            f"Approximate context window usage for {self.coder.main_model.name}, in tokens:"
        )
        self.io.tool_output()

        width = 8
        cost_width = 9

        def fmt(v):
            return format(int(v), ",").rjust(width)

        col_width = max(len(row[1]) for row in res)

        cost_pad = " " * cost_width
        total = 0
        total_cost = 0.0
        for tk, msg, tip in res:
            total += tk
            cost = tk * (self.coder.main_model.info.get("input_cost_per_token") or 0)
            total_cost += cost
            msg = msg.ljust(col_width)
            self.io.tool_output(f"${cost:7.4f} {fmt(tk)} {msg} {tip}")  # noqa: E231

        self.io.tool_output("=" * (width + cost_width + 1))
        self.io.tool_output(f"${total_cost:7.4f} {fmt(total)} tokens total")  # noqa: E231

        limit = self.coder.main_model.info.get("max_input_tokens") or 0
        if not limit:
            return

        remaining = limit - total
        if remaining > 1024:
            self.io.tool_output(
                f"{cost_pad}{fmt(remaining)} tokens remaining in context window"
            )
        elif remaining > 0:
            self.io.tool_error(
                f"{cost_pad}{fmt(remaining)} tokens remaining in context window (use /drop or"
                " /clear to make space)"
            )
        else:
            self.io.tool_error(
                f"{cost_pad}{fmt(remaining)} tokens remaining, window exhausted (use /drop or"
                " /clear to make space)"
            )
        self.io.tool_output(f"{cost_pad}{fmt(limit)} tokens max context window size")

    def cmd_undo(self, args):
        "Undo the last git commit if it was done by lsr"
        try:
            self.raw_cmd_undo(args)
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to complete undo: {err}")

    def raw_cmd_undo(self, args):
        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        last_commit = self.coder.repo.get_head_commit()
        if not last_commit or not last_commit.parents:
            self.io.tool_error(
                "This is the first commit in the repository. Cannot undo."
            )
            return

        last_commit_hash = self.coder.repo.get_head_commit_sha(short=True)
        last_commit_message = self.coder.repo.get_head_commit_message(
            "(unknown)"
        ).strip()
        last_commit_message = (last_commit_message.splitlines() or [""])[0]
        if last_commit_hash not in self.coder.lsr_commit_hashes:
            self.io.tool_error(
                "The last commit was not made by lsr in this chat session."
            )
            self.io.tool_output(
                "You could try `/git reset --hard HEAD^` but be aware that this is a destructive"
                " command!"
            )
            return

        if len(last_commit.parents) > 1:
            self.io.tool_error(
                f"The last commit {last_commit.hexsha} has more than 1 parent, can't undo."
            )
            return

        prev_commit = last_commit.parents[0]
        changed_files_last_commit = [
            item.a_path for item in last_commit.diff(prev_commit)
        ]

        for fname in changed_files_last_commit:
            if self.coder.repo.repo.is_dirty(path=fname):
                self.io.tool_error(
                    f"The file {fname} has uncommitted changes. Please stash them before undoing."
                )
                return

            # Check if the file was in the repo in the previous commit
            try:
                prev_commit.tree[fname]
            except KeyError:
                self.io.tool_error(
                    f"The file {fname} was not in the repository in the previous commit. Cannot"
                    " undo safely."
                )
                return

        local_head = self.coder.repo.repo.git.rev_parse("HEAD")
        current_branch = self.coder.repo.repo.active_branch.name
        try:
            remote_head = self.coder.repo.repo.git.rev_parse(f"origin/{current_branch}")
            has_origin = True
        except ANY_GIT_ERROR:
            has_origin = False

        if has_origin:
            if local_head == remote_head:
                self.io.tool_error(
                    "The last commit has already been pushed to the origin. Undoing is not"
                    " possible."
                )
                return

        # Reset only the files which are part of `last_commit`
        restored = set()
        unrestored = set()
        for file_path in changed_files_last_commit:
            try:
                self.coder.repo.repo.git.checkout("HEAD~1", file_path)
                restored.add(file_path)
            except ANY_GIT_ERROR:
                unrestored.add(file_path)

        if unrestored:
            self.io.tool_error(f"Error restoring {file_path}, aborting undo.")
            self.io.tool_output("Restored files:")
            for file in restored:
                self.io.tool_output(f"  {file}")
            self.io.tool_output("Unable to restore files:")
            for file in unrestored:
                self.io.tool_output(f"  {file}")
            return

        # Move the HEAD back before the latest commit
        self.coder.repo.repo.git.reset("--soft", "HEAD~1")

        self.io.tool_output(f"Removed: {last_commit_hash} {last_commit_message}")

        # Get the current HEAD after undo
        current_head_hash = self.coder.repo.get_head_commit_sha(short=True)
        current_head_message = self.coder.repo.get_head_commit_message(
            "(unknown)"
        ).strip()
        current_head_message = (current_head_message.splitlines() or [""])[0]
        self.io.tool_output(f"Now at:  {current_head_hash} {current_head_message}")

        if self.coder.main_model.send_undo_reply:
            return prompts.undo_command_reply

    def cmd_diff(self, args=""):
        "Display the diff of changes since the last message"
        try:
            self.raw_cmd_diff(args)
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to complete diff: {err}")

    def raw_cmd_diff(self, args=""):
        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        current_head = self.coder.repo.get_head_commit_sha()
        if current_head is None:
            self.io.tool_error(
                "Unable to get current commit. The repository might be empty."
            )
            return

        if len(self.coder.commit_before_message) < 2:
            commit_before_message = current_head + "^"
        else:
            commit_before_message = self.coder.commit_before_message[-2]

        if not commit_before_message or commit_before_message == current_head:
            self.io.tool_warning("No changes to display since the last message.")
            return

        self.io.tool_output(f"Diff since {commit_before_message[:7]}...")

        if self.coder.pretty:
            run_cmd(f"git diff {commit_before_message}")
            return

        diff = self.coder.repo.diff_commits(
            self.coder.pretty,
            commit_before_message,
            "HEAD",
        )

        self.io.print(diff)

    def quote_fname(self, fname):
        if " " in fname and '"' not in fname:
            fname = f'"{fname}"'
        return fname

    def completions_raw_read_only(self, document, complete_event):
        # Get the text before the cursor
        text = document.text_before_cursor

        # Skip the first word and the space after it
        after_command = text.split()[-1]

        # Create a new Document object with the text after the command
        new_document = Document(after_command, cursor_position=len(after_command))

        def get_paths():
            return [self.coder.root] if self.coder.root else None

        path_completer = PathCompleter(
            get_paths=get_paths,
            only_directories=False,
            expanduser=True,
        )

        # Adjust the start_position to replace all of 'after_command'
        adjusted_start_position = -len(after_command)

        # Collect all completions
        all_completions = []

        # Iterate over the completions and modify them
        for completion in path_completer.get_completions(new_document, complete_event):
            quoted_text = self.quote_fname(after_command + completion.text)
            all_completions.append(
                Completion(
                    text=quoted_text,
                    start_position=adjusted_start_position,
                    display=completion.display,
                    style=completion.style,
                    selected_style=completion.selected_style,
                )
            )

        # Add completions from the 'add' command
        add_completions = self.completions_add()
        for completion in add_completions:
            if after_command in completion:
                all_completions.append(
                    Completion(
                        text=completion,
                        start_position=adjusted_start_position,
                        display=completion,
                    )
                )

        # Sort all completions based on their text
        sorted_completions = sorted(all_completions, key=lambda c: c.text)

        # Yield the sorted completions
        for completion in sorted_completions:
            yield completion

    def completions_add(self):
        files = set(self.coder.get_all_relative_files())
        files = files - set(self.coder.get_inchat_relative_files())
        files = [self.quote_fname(fn) for fn in files]
        return files

    def completions_edit(self):
        """Provide .tex file completions for /edit command."""
        all_files = set(self.coder.get_all_relative_files())
        inchat_files = set(self.coder.get_inchat_relative_files())
        tex_files = all_files | inchat_files
        tex_files = [f for f in tex_files if f.endswith(".tex")]
        tex_files = [self.quote_fname(fn) for fn in tex_files]
        return tex_files

    def completions_mark(self):
        """Provide completions for /mark command: --reset flag and .tex files."""
        return ["--reset"] + self.completions_edit()

    def glob_filtered_to_repo(self, pattern):
        if not pattern.strip():
            return []
        try:
            if os.path.isabs(pattern):
                # Handle absolute paths
                raw_matched_files = [Path(pattern)]
            else:
                try:
                    # 根据 use_cwd 设置决定使用当前工作目录还是 Git 根目录
                    if self.coder.use_cwd:
                        raw_matched_files = list(Path.cwd().glob(pattern))
                    else:
                        raw_matched_files = list(Path(self.coder.root).glob(pattern))
                except (IndexError, AttributeError):
                    raw_matched_files = []
        except ValueError as err:
            self.io.tool_error(f"Error matching {pattern}: {err}")
            raw_matched_files = []

        matched_files = []
        for fn in raw_matched_files:
            matched_files += expand_subdir(fn)

        # 根据 use_cwd 设置决定使用哪个根目录进行相对路径计算
        if self.coder.use_cwd:
            root = Path.cwd()
        else:
            root = Path(self.coder.root)

        matched_files = [
            fn.relative_to(root) for fn in matched_files if fn.is_relative_to(root)
        ]

        # if repo, filter against it
        if self.coder.repo:
            git_files = self.coder.repo.get_tracked_files()
            matched_files = [fn for fn in matched_files if str(fn) in git_files]

        res = list(map(str, matched_files))
        return res

    def cmd_add(self, args):
        "Add files to the chat so lsr can edit them or review them in detail"

        all_matched_files = set()

        filenames = parse_quoted_filenames(args)
        for word in filenames:
            if Path(word).is_absolute():
                fname = Path(word)
            else:
                # 根据 use_cwd 设置决定使用当前工作目录还是 Git 根目录
                if self.coder.use_cwd:
                    fname = Path.cwd() / word
                else:
                    fname = Path(self.coder.root) / word

            if self.coder.repo and self.coder.repo.ignored_file(fname):
                self.io.tool_warning(
                    f"Skipping {fname} due to lsrignore or --subtree-only."
                )
                continue

            if fname.exists():
                if fname.is_file():
                    all_matched_files.add(str(fname))
                    continue
                # an existing dir, escape any special chars so they won't be globs
                word = re.sub(r"([\*\?\[\]])", r"[\1]", word)

            matched_files = self.glob_filtered_to_repo(word)
            if matched_files:
                all_matched_files.update(matched_files)
                continue

            if "*" in str(fname) or "?" in str(fname):
                self.io.tool_error(
                    f"No match, and cannot create file with wildcard characters: {fname}"
                )
                continue

            if fname.exists() and fname.is_dir() and self.coder.repo:
                self.io.tool_error(f"Directory {fname} is not in git.")
                self.io.tool_output(f"You can add to git with: /git add {fname}")
                continue

            if self.io.confirm_ask(
                f"No files matched '{word}'. Do you want to create {fname}?"
            ):
                try:
                    fname.parent.mkdir(parents=True, exist_ok=True)
                    fname.touch()
                    all_matched_files.add(str(fname))
                except OSError as e:
                    self.io.tool_error(f"Error creating file {fname}: {e}")

        for matched_file in sorted(all_matched_files):
            abs_file_path = self.coder.abs_root_path(matched_file)

            if (
                not abs_file_path.startswith(self.coder.root)
                and not is_image_file(matched_file)
                and self.coder.auto_commits
            ):
                self.io.tool_error(
                    f"Can not add {abs_file_path}, which is not within {self.coder.root}"
                )
                continue

            if (
                self.coder.repo
                and self.coder.repo.git_ignored_file(matched_file)
                and not self.coder.add_gitignore_files
            ):
                self.io.tool_error(f"Can't add {matched_file} which is in gitignore")
                continue

            if abs_file_path in self.coder.abs_fnames:
                self.io.tool_error(
                    f"{matched_file} is already in the chat as an editable file"
                )
                continue
            elif abs_file_path in self.coder.abs_read_only_fnames:
                # Determine if file can be promoted to editable
                if self.coder.repo:
                    can_edit = self.coder.repo.path_in_repo(matched_file)
                else:
                    can_edit = abs_file_path.startswith(self.coder.root)

                if can_edit:
                    self.coder.abs_read_only_fnames.remove(abs_file_path)
                    self.coder.abs_fnames.add(abs_file_path)
                    self.io.tool_output(
                        f"Moved {matched_file} from read-only to editable files in the chat"
                    )
                else:
                    self.io.tool_error(
                        f"Cannot add {matched_file} as it's not part of the repository"
                    )
            else:
                if is_image_file(matched_file) and not self.coder.main_model.info.get(
                    "supports_vision"
                ):
                    self.io.tool_error(
                        f"Cannot add image file {matched_file} as the"
                        f" {self.coder.main_model.name} does not support images."
                    )
                    continue
                content = self.io.read_text(abs_file_path)
                if content is None:
                    self.io.tool_error(f"Unable to read {matched_file}")
                else:
                    self.coder.abs_fnames.add(abs_file_path)
                    fname = self.coder.get_rel_fname(abs_file_path)
                    self.io.tool_output(f"Added {fname} to the chat")
                    self.coder.check_added_files()

    def completions_drop(self):
        files = self.coder.get_inchat_relative_files()
        read_only_files = [
            self.coder.get_rel_fname(fn) for fn in self.coder.abs_read_only_fnames
        ]
        all_files = files + read_only_files
        all_files = [self.quote_fname(fn) for fn in all_files]
        return all_files

    def cmd_drop(self, args=""):
        "Remove files from the chat session to free up context space"

        if not args.strip():
            if self.original_read_only_fnames:
                self.io.tool_output(
                    "Dropping all files from the chat session except originally read-only files."
                )
            else:
                self.io.tool_output("Dropping all files from the chat session.")
            self._drop_all_files()
            return

        filenames = parse_quoted_filenames(args)
        for word in filenames:
            # Expand tilde in the path
            expanded_word = os.path.expanduser(word)

            # Handle read-only files with substring matching and samefile check
            read_only_matched = []
            for f in self.coder.abs_read_only_fnames:
                if expanded_word in f:
                    read_only_matched.append(f)
                    continue

                # Try samefile comparison for relative paths
                try:
                    abs_word = os.path.abspath(expanded_word)
                    if os.path.samefile(abs_word, f):
                        read_only_matched.append(f)
                except (FileNotFoundError, OSError):
                    continue

            for matched_file in read_only_matched:
                self.coder.abs_read_only_fnames.remove(matched_file)
                self.io.tool_output(
                    f"Removed read-only file {matched_file} from the chat"
                )

            # For editable files, use glob if word contains glob chars, otherwise use substring
            if any(c in expanded_word for c in "*?[]"):
                matched_files = self.glob_filtered_to_repo(expanded_word)
            else:
                # Use substring matching like we do for read-only files
                matched_files = [
                    self.coder.get_rel_fname(f)
                    for f in self.coder.abs_fnames
                    if expanded_word in f
                ]

            if not matched_files:
                matched_files.append(expanded_word)

            for matched_file in matched_files:
                abs_fname = self.coder.abs_root_path(matched_file)
                if abs_fname in self.coder.abs_fnames:
                    self.coder.abs_fnames.remove(abs_fname)
                    self.io.tool_output(f"Removed {matched_file} from the chat")

    def cmd_git(self, args):
        "Run a git command (output excluded from chat)"
        combined_output = None
        try:
            args = "git " + args
            env = dict(subprocess.os.environ)
            env["GIT_EDITOR"] = "true"
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                shell=True,
                encoding=self.io.encoding,
                errors="replace",
            )
            combined_output = result.stdout
        except Exception as e:
            self.io.tool_error(f"Error running /git command: {e}")

        if combined_output is None:
            return

        self.io.tool_output(combined_output)

    def cmd_compile(self, args):
        "Run LaTeX compilation and add the output to the chat on non-zero exit code"
        if not args and self.coder.test_cmd:
            args = self.coder.test_cmd

        if not args:
            return

        if not callable(args):
            if type(args) is not str:
                raise ValueError(repr(args))
            return self.cmd_run(args, True)

        errors = args()
        if not errors:
            return

        self.io.tool_output(errors)
        return errors

    def _parse_latex_log(self, log_file):
        """Parse LaTeX log file and extract key information."""
        if not os.path.exists(log_file):
            return None

        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        lines = content.split("\n")
        errors = []
        warnings = []
        undefined_refs = []
        missing_files = []
        latex_errors = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # LaTeX errors (start with !)
            if line.startswith("!"):
                error_context = []
                for j in range(max(0, i - 2), min(len(lines), i + 3)):
                    error_context.append(lines[j])
                latex_errors.append(
                    {
                        "line_num": i + 1,
                        "content": line,
                        "context": "\n".join(error_context),
                    }
                )

            # Errors
            if "Error" in line or "error" in line:
                errors.append({"line_num": i + 1, "content": line})

            # Warnings
            if "Warning" in line and "Reference" not in line:
                warnings.append({"line_num": i + 1, "content": line})

            # Undefined references
            if "undefined" in line.lower() or "multiply defined" in line.lower():
                undefined_refs.append({"line_num": i + 1, "content": line})

            # Missing files
            if "File" in line and "not found" in line:
                missing_files.append({"line_num": i + 1, "content": line})

            i += 1

        # Build summary
        summary_parts = []

        if latex_errors:
            summary_parts.append("## LaTeX 错误")
            for err in latex_errors[:5]:
                summary_parts.append(f"- 行 {err['line_num']}: {err['content']}")
                summary_parts.append(f"  上下文:\n```\n{err['context']}\n```")

        if errors:
            summary_parts.append("\n## 编译错误")
            for err in errors[:10]:
                summary_parts.append(f"- 行 {err['line_num']}: {err['content']}")

        if undefined_refs:
            summary_parts.append("\n## 未定义引用")
            for ref in undefined_refs[:10]:
                summary_parts.append(f"- 行 {ref['line_num']}: {ref['content']}")

        if missing_files:
            summary_parts.append("\n## 缺失文件")
            for f in missing_files[:5]:
                summary_parts.append(f"- 行 {f['line_num']}: {f['content']}")

        if warnings:
            summary_parts.append("\n## 警告")
            for w in warnings[:10]:
                summary_parts.append(f"- 行 {w['line_num']}: {w['content']}")
            if len(warnings) > 10:
                summary_parts.append(f"- ... 还有 {len(warnings) - 10} 个警告")

        if not summary_parts:
            return None

        return {
            "summary": "\n".join(summary_parts),
            "stats": {
                "errors": len(errors) + len(latex_errors),
                "warnings": len(warnings),
                "undefined_refs": len(undefined_refs),
                "missing_files": len(missing_files),
            },
            "has_errors": len(latex_errors) > 0 or len(errors) > 0,
        }

    def _ask_add_log_to_context(self, tex_file, log_info):
        """Ask user if they want to add log analysis to LLM context."""
        if not log_info:
            return

        stats = log_info["stats"]
        self.io.tool_output("\n" + "=" * 50)
        self.io.tool_output("📊 日志分析摘要:")
        self.io.tool_output(f"  - 错误: {stats['errors']}")
        self.io.tool_output(f"  - 警告: {stats['warnings']}")
        self.io.tool_output(f"  - 未定义引用: {stats['undefined_refs']}")
        self.io.tool_output(f"  - 缺失文件: {stats['missing_files']}")

        if stats["errors"] == 0 and stats["warnings"] == 0:
            self.io.tool_output("\n✅ 没有发现错误或警告，无需添加到上下文。")
            return

        # Ask user confirmation
        self.io.tool_output("\n是否将日志分析结果添加到 LLM 上下文？")
        self.io.tool_output("  [y] 是 - 添加到上下文")
        self.io.tool_output("  [n] 否 - 跳过 (默认)")

        try:
            user_input = self.io.confirm_ask(
                "添加日志分析到上下文？",
                default="n",
            )
        except (EOFError, KeyboardInterrupt):
            user_input = False

        if user_input:
            # Add to LLM context
            basename = os.path.basename(tex_file)
            log_content = f"## LaTeX 编译日志分析 ({basename})\n\n{log_info['summary']}"

            self.coder.cur_messages += [
                dict(
                    role="user",
                    content=f"请帮我分析并修复以下 LaTeX 编译问题:\n\n{log_content}",
                ),
                dict(
                    role="assistant", content="我来帮你分析并修复这些 LaTeX 编译问题。"
                ),
            ]

            self.io.tool_output("\n✅ 已将日志分析结果添加到 LLM 上下文。")
            self.io.tool_output("你可以在下一条消息中询问 LLM 如何修复这些问题。")
        else:
            self.io.tool_output("\n⏭️  已跳过，未添加到上下文。")

    def _run_latex_compile(self, engine, args):
        """Helper function to run LaTeX compilation."""
        import subprocess

        # Find .tex file to compile
        tex_file = None
        if args:
            tex_file = args.strip()
        else:
            # Auto-detect main .tex file
            for f in self.coder.abs_fnames:
                if f.endswith(".tex"):
                    tex_file = f
                    break
            if not tex_file:
                # Look for .tex files in current directory
                import glob

                tex_files = glob.glob(os.path.join(self.coder.root or ".", "*.tex"))
                if tex_files:
                    tex_file = tex_files[0]

        if not tex_file:
            self.io.tool_error("No .tex file found. Use: /xelatex <file.tex>")
            return

        if not os.path.exists(tex_file):
            self.io.tool_error(f"File not found: {tex_file}")
            return

        self.io.tool_output(
            f"\n🔨 Compiling with {engine}: {os.path.basename(tex_file)}"
        )
        self.io.tool_output("=" * 50)

        # Run LaTeX compiler
        try:
            result = subprocess.run(
                [
                    engine,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    os.path.basename(tex_file),
                ],
                cwd=os.path.dirname(os.path.abspath(tex_file)) or ".",
                capture_output=True,
                text=True,
                timeout=120,
            )

            output = result.stdout + result.stderr

            if result.returncode == 0:
                self.io.tool_output("\n✅ Compilation successful!")
                # Show warnings if any
                warnings = [line for line in output.split("\n") if "Warning" in line]
                if warnings:
                    self.io.tool_output(f"\n⚠️  Warnings ({len(warnings)}):")
                    for w in warnings[:5]:
                        self.io.tool_output(f"  {w}")
                    if len(warnings) > 5:
                        self.io.tool_output(f"  ... and {len(warnings) - 5} more")
            else:
                self.io.tool_output(
                    f"\n❌ Compilation failed (exit code {result.returncode})"
                )
                # Extract error lines
                error_lines = []
                for line in output.split("\n"):
                    if line.startswith("!") or "Error" in line or "error" in line:
                        error_lines.append(line)
                if error_lines:
                    self.io.tool_output("\nErrors:")
                    for e in error_lines[:10]:
                        self.io.tool_output(f"  {e}")

            # Parse log file and ask user if they want to add to context
            log_file = os.path.splitext(tex_file)[0] + ".log"
            log_info = self._parse_latex_log(log_file)
            self._ask_add_log_to_context(tex_file, log_info)

            if result.returncode != 0:
                return output

        except FileNotFoundError:
            self.io.tool_error(
                f"{engine} not found. Please install TeX Live or MiKTeX."
            )
        except subprocess.TimeoutExpired:
            self.io.tool_error("Compilation timed out (120s limit)")
        except Exception as e:
            self.io.tool_error(f"Error: {e}")

    def cmd_xelatex(self, args=""):
        """Compile LaTeX file with xelatex engine"""
        self._run_latex_compile("xelatex", args)

    def cmd_pdflatex(self, args=""):
        """Compile LaTeX file with pdflatex engine"""
        self._run_latex_compile("pdflatex", args)

    def _run_latex_compile_with_bib(self, engine, args):
        """Helper function to run LaTeX compilation with bibliography."""
        import subprocess
        import os
        import glob

        # Find .tex file to compile
        tex_file = None
        if args:
            tex_file = args.strip()
        else:
            # Auto-detect main .tex file
            for f in self.coder.abs_fnames:
                if f.endswith(".tex"):
                    tex_file = f
                    break
            if not tex_file:
                # Look for .tex files in current directory
                tex_files = glob.glob(os.path.join(self.coder.root or ".", "*.tex"))
                if tex_files:
                    tex_file = tex_files[0]

        if not tex_file:
            self.io.tool_error(f"No .tex file found. Use: /bib-{engine} <file.tex>")
            return

        if not os.path.exists(tex_file):
            self.io.tool_error(f"File not found: {tex_file}")
            return

        basename = os.path.basename(tex_file)
        basename_no_ext = os.path.splitext(basename)[0]
        cwd = os.path.dirname(os.path.abspath(tex_file)) or "."

        self.io.tool_output(f"\n🔨 Compiling with {engine} + bibtex: {basename}")
        self.io.tool_output("=" * 50)

        steps = [
            (engine, f"Step 1/4: {engine}"),
            ("bibtex", "Step 2/4: bibtex"),
            (engine, f"Step 3/4: {engine}"),
            (engine, f"Step 4/4: {engine}"),
        ]

        final_output = None
        for i, (cmd, step_name) in enumerate(steps):
            self.io.tool_output(f"\n⏳ {step_name}...")
            try:
                if cmd == "bibtex":
                    result = subprocess.run(
                        [cmd, basename_no_ext],
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                else:
                    result = subprocess.run(
                        [
                            cmd,
                            "-interaction=nonstopmode",
                            "-halt-on-error",
                            basename,
                        ],
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                output = result.stdout + result.stderr
                final_output = output

                if result.returncode != 0:
                    self.io.tool_output(
                        f"\n❌ {step_name} failed (exit code {result.returncode})"
                    )
                    # Extract error lines
                    error_lines = []
                    for line in output.split("\n"):
                        if line.startswith("!") or "Error" in line or "error" in line:
                            error_lines.append(line)
                    if error_lines:
                        self.io.tool_output("\nErrors:")
                        for e in error_lines[:10]:
                            self.io.tool_output(f"  {e}")

                    # Parse log file and ask user if they want to add to context
                    log_file = os.path.splitext(tex_file)[0] + ".log"
                    log_info = self._parse_latex_log(log_file)
                    self._ask_add_log_to_context(tex_file, log_info)
                    return output
                else:
                    self.io.tool_output(f"  ✅ {step_name} completed")

            except FileNotFoundError:
                self.io.tool_error(
                    f"{cmd} not found. Please install TeX Live or MiKTeX."
                )
                return
            except subprocess.TimeoutExpired:
                self.io.tool_error(f"{step_name} timed out (120s limit)")
                return
            except Exception as e:
                self.io.tool_error(f"Error in {step_name}: {e}")
                return

        self.io.tool_output("\n" + "=" * 50)
        self.io.tool_output("✅ Full compilation with bibliography successful!")

        # Show warnings from final compilation
        if final_output:
            warnings = [line for line in final_output.split("\n") if "Warning" in line]
            if warnings:
                self.io.tool_output(f"\n⚠️  Warnings ({len(warnings)}):")
                for w in warnings[:5]:
                    self.io.tool_output(f"  {w}")
                if len(warnings) > 5:
                    self.io.tool_output(f"  ... and {len(warnings) - 5} more")

        # Parse log file and ask user if they want to add to context
        log_file = os.path.splitext(tex_file)[0] + ".log"
        log_info = self._parse_latex_log(log_file)
        self._ask_add_log_to_context(tex_file, log_info)

    def cmd_bib_pdflatex(self, args=""):
        """Compile LaTeX file with pdflatex engine and bibliography (pdflatex -> bibtex -> pdflatex -> pdflatex)"""
        self._run_latex_compile_with_bib("pdflatex", args)

    def cmd_bib_xelatex(self, args=""):
        """Compile LaTeX file with xelatex engine and bibliography (xelatex -> bibtex -> xelatex -> xelatex)"""
        self._run_latex_compile_with_bib("xelatex", args)

    def cmd_run(self, args, add_on_nonzero_exit=False):
        "Run a shell command and optionally add the output to the chat (alias: !)"
        exit_status, combined_output = run_cmd(
            args,
            verbose=self.verbose,
            error_print=self.io.tool_error,
            cwd=self.coder.root,
        )

        if combined_output is None:
            return

        # Calculate token count of output
        token_count = self.coder.main_model.token_count(combined_output)
        k_tokens = token_count / 1000

        if add_on_nonzero_exit:
            add = exit_status != 0
        else:
            add = self.io.confirm_ask(
                f"Add {k_tokens:.1f}k tokens of command output to the chat?"
            )

        if add:
            num_lines = len(combined_output.strip().splitlines())
            line_plural = "line" if num_lines == 1 else "lines"
            self.io.tool_output(
                f"Added {num_lines} {line_plural} of output to the chat."
            )

            msg = prompts.run_output.format(
                command=args,
                output=combined_output,
            )

            self.coder.cur_messages += [
                dict(role="user", content=msg),
                dict(role="assistant", content="Ok."),
            ]

            if add_on_nonzero_exit and exit_status != 0:
                # Return the formatted output message for test failures
                return msg
            elif add and exit_status != 0:
                self.io.placeholder = "What's wrong? Fix"

        # Return None if output wasn't added or command succeeded
        return None

    def cmd_exit(self, args):
        "Exit the application"
        sys.exit()

    def cmd_quit(self, args):
        "Exit the application"
        self.cmd_exit(args)

    def cmd_ls(self, args):
        "List all known files and indicate which are included in the chat session"

        files = self.coder.get_all_relative_files()

        other_files = []
        chat_files = []
        read_only_files = []
        for file in files:
            abs_file_path = self.coder.abs_root_path(file)
            if abs_file_path in self.coder.abs_fnames:
                chat_files.append(file)
            else:
                other_files.append(file)

        # Add read-only files
        for abs_file_path in self.coder.abs_read_only_fnames:
            rel_file_path = self.coder.get_rel_fname(abs_file_path)
            read_only_files.append(rel_file_path)

        if not chat_files and not other_files and not read_only_files:
            self.io.tool_output("\nNo files in chat, git repo, or read-only list.")
            return

        if other_files:
            self.io.tool_output("Repo files not in the chat:\n")
        for file in other_files:
            self.io.tool_output(f"  {file}")

        if read_only_files:
            self.io.tool_output("\nRead-only files:\n")
        for file in read_only_files:
            self.io.tool_output(f"  {file}")

        if chat_files:
            self.io.tool_output("\nFiles in chat:\n")
        for file in chat_files:
            self.io.tool_output(f"  {file}")

    def basic_help(self):
        commands = sorted(self.get_commands())
        pad = max(len(cmd) for cmd in commands)
        pad = "{cmd:" + str(pad) + "}"
        for cmd in commands:
            cmd_method_name = f"cmd_{cmd[1:]}".replace("-", "_")
            cmd_method = getattr(self, cmd_method_name, None)
            cmd = pad.format(cmd=cmd)
            if cmd_method:
                description = cmd_method.__doc__
                self.io.tool_output(f"{cmd} {description}")
            else:
                self.io.tool_output(f"{cmd} No description available.")
        self.io.tool_output()
        self.io.tool_output(
            "Use `/help <question>` to ask questions about how to use lsr."
        )

    def cmd_help(self, args):
        "Ask questions about lsr"

        if not args.strip():
            self.basic_help()
            return

        from lsr.coders.base_coder import Coder

        if not self.help:
            res = install_help_extra(self.io)
            if not res:
                self.io.tool_error("Unable to initialize interactive help.")
                return

            self.help = Help()

        coder = Coder.create(
            io=self.io,
            from_coder=self.coder,
            edit_format="help",
            summarize_from_coder=False,
            map_tokens=512,
            map_mul_no_files=1,
        )
        user_msg = self.help.ask(args)
        user_msg += """
# Announcement lines from when this session of lsr was launched:

"""
        user_msg += "\n".join(self.coder.get_announcements()) + "\n"

        coder.run(user_msg, preproc=False)

        if self.coder.repo_map:
            map_tokens = self.coder.repo_map.max_map_tokens
            map_mul_no_files = self.coder.repo_map.map_mul_no_files
        else:
            map_tokens = 0
            map_mul_no_files = 1

        raise SwitchCoder(
            edit_format=self.coder.edit_format,
            summarize_from_coder=False,
            from_coder=coder,
            map_tokens=map_tokens,
            map_mul_no_files=map_mul_no_files,
            show_announcements=False,
        )

    def completions_ask(self):
        raise CommandCompletionException()

    def completions_code(self):
        raise CommandCompletionException()

    def completions_architect(self):
        raise CommandCompletionException()

    def completions_context(self):
        raise CommandCompletionException()

    def cmd_ask(self, args):
        """Ask questions about the code base without editing any files. If no prompt provided, switches to ask mode."""  # noqa
        return self._generic_chat_command(args, "ask")

    def cmd_plan(self, args):
        """Create a structured plan before coding. Subcommands: list, show, use, delete."""  # noqa
        from lsr.plan_manager import (
            delete_plan,
            find_plan_by_id_or_latest,
            list_plans,
            load_plan,
        )

        tokens = args.strip().split(None, 1)
        subcommand = tokens[0].lower() if tokens else ""

        # Subcommand routing
        if subcommand == "list":
            plans = list_plans(self.coder.root)
            if not plans:
                self.io.tool_output("No plans found.")
                return
            self.io.tool_output("Saved plans:")
            self.io.tool_output(f"  {'ID':<10s}  {'Status':<10s}  Title")
            self.io.tool_output(f"  {'-' * 10}  {'-' * 10}  {'-' * 40}")
            for p in plans:
                self.io.tool_output(f"  {p.short_id:<10s}  {p.status:<10s}  {p.title}")
            return

        if subcommand == "show":
            plan_id = tokens[1].strip() if len(tokens) > 1 else ""
            plan = find_plan_by_id_or_latest(plan_id or None, self.coder.root)
            if not plan:
                self.io.tool_error(f"Plan not found: {plan_id or '(latest)'}")
                return
            self.io.tool_output(
                f"Plan: {plan.title}  (id={plan.short_id}, status={plan.status})"
            )
            self.io.tool_output("")
            self.io.tool_output(plan.content)
            return

        if subcommand == "use":
            plan_id = tokens[1].strip() if len(tokens) > 1 else ""
            plan = load_plan(plan_id, self.coder.root) if plan_id else None
            if not plan:
                self.io.tool_error(f"Plan not found: {plan_id}")
                return
            self.coder.current_plan = plan.content
            self.io.tool_output(
                f"Loaded plan '{plan.title}' ({plan.short_id}) into context."
            )
            self.io.tool_output("Type `/code` to execute it.")
            return

        if subcommand == "delete":
            plan_id = tokens[1].strip() if len(tokens) > 1 else ""
            if not plan_id:
                self.io.tool_error("Usage: /plan delete <id>")
                return
            if delete_plan(plan_id, self.coder.root):
                self.io.tool_output(f"Deleted plan {plan_id}.")
            else:
                self.io.tool_error(f"Plan not found: {plan_id}")
            return

        # No subcommand → generate a new plan via LLM
        return self._generic_chat_command(args, "plan")

    def cmd_code(self, args):
        """Ask for changes to your code. If no prompt provided, switches to code mode."""  # noqa
        # Inject stored plan into the user message when executing in code mode
        if getattr(self.coder, "current_plan", None) and args.strip():
            plan_context = self.coder.current_plan[:2000]
            if len(self.coder.current_plan) > 2000:
                plan_context += "\n... (plan truncated)"
            args = (
                f"Execute the following approved plan:\n\n{plan_context}\n\n"
                f"User request: {args}"
            )
        return self._generic_chat_command(args, self.coder.main_model.edit_format)

    def cmd_ok(self, args):
        "Alias for `/code Ok, please go ahead and make those changes.` (any args are appended)"
        msg = "Ok, please go ahead and make those changes."
        extra = (args or "").strip()
        if extra:
            msg = f"{msg} {extra}"
        return self.cmd_code(msg)

    def _generic_chat_command(self, args, edit_format, placeholder=None):
        if not args.strip():
            # Switch to the corresponding chat mode if no args provided
            return self.cmd_chat_mode(edit_format)

        from lsr.coders.base_coder import Coder

        coder = Coder.create(
            io=self.io,
            from_coder=self.coder,
            edit_format=edit_format,
            summarize_from_coder=False,
        )

        user_msg = args
        coder.run(user_msg)

        # Use the provided placeholder if any
        raise SwitchCoder(
            edit_format=self.coder.edit_format,
            summarize_from_coder=False,
            from_coder=coder,
            show_announcements=False,
            placeholder=placeholder,
        )

    def _generic_chat_command_for_file(self, target_file, user_msg, edit_format):
        """Like _generic_chat_command but targets a specific file for LLM edits.

        Creates a coder with ONLY the target file in fnames, so the LLM
        context is focused on that file. The file content is read automatically
        by get_files_content() during format_messages().
        """
        from lsr.coders.base_coder import Coder

        coder = Coder.create(
            io=self.io,
            from_coder=self.coder,
            fnames=[target_file],
            edit_format=edit_format,
            summarize_from_coder=False,
        )

        coder.run(user_msg)

        raise SwitchCoder(
            edit_format=self.coder.edit_format,
            summarize_from_coder=False,
            from_coder=coder,
            show_announcements=False,
        )

    def get_help_md(self):
        "Show help about all commands in markdown"

        res = """
|Command|Description|
|:------|:----------|
"""
        commands = sorted(self.get_commands())
        for cmd in commands:
            cmd_method_name = f"cmd_{cmd[1:]}".replace("-", "_")
            cmd_method = getattr(self, cmd_method_name, None)
            if cmd_method:
                description = cmd_method.__doc__
                res += f"| **{cmd}** | {description} |\n"
            else:
                res += f"| **{cmd}** | |\n"

        res += "\n"
        return res

    def cmd_paste(self, args):
        """Paste image/text from the clipboard into the chat.\
        Optionally provide a name for the image."""
        try:
            # Check for image first
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                if args.strip():
                    filename = args.strip()
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in (".jpg", ".jpeg", ".png"):
                        basename = filename
                    else:
                        basename = f"{filename}.png"
                else:
                    basename = "clipboard_image.png"

                temp_dir = tempfile.mkdtemp()
                temp_file_path = os.path.join(temp_dir, basename)
                image_format = "PNG" if basename.lower().endswith(".png") else "JPEG"
                image.save(temp_file_path, image_format)

                abs_file_path = Path(temp_file_path).resolve()

                # Check if a file with the same name already exists in the chat
                existing_file = next(
                    (
                        f
                        for f in self.coder.abs_fnames
                        if Path(f).name == abs_file_path.name
                    ),
                    None,
                )
                if existing_file:
                    self.coder.abs_fnames.remove(existing_file)
                    self.io.tool_output(
                        f"Replaced existing image in the chat: {existing_file}"
                    )

                self.coder.abs_fnames.add(str(abs_file_path))
                self.io.tool_output(
                    f"Added clipboard image to the chat: {abs_file_path}"
                )
                self.coder.check_added_files()

                return

            # If not an image, try to get text
            text = pyperclip.paste()
            if text:
                self.io.tool_output(text)
                return text

            self.io.tool_error("No image or text content found in clipboard.")
            return

        except Exception as e:
            self.io.tool_error(f"Error processing clipboard content: {e}")

    def cmd_read_only(self, args):
        "Add files to the chat that are for reference only, or turn added files to read-only"
        if not args.strip():
            # Convert all files in chat to read-only
            for fname in list(self.coder.abs_fnames):
                self.coder.abs_fnames.remove(fname)
                self.coder.abs_read_only_fnames.add(fname)
                rel_fname = self.coder.get_rel_fname(fname)
                self.io.tool_output(f"Converted {rel_fname} to read-only")
            return

        filenames = parse_quoted_filenames(args)
        all_paths = []

        # First collect all expanded paths
        for pattern in filenames:
            expanded_pattern = expanduser(pattern)
            path_obj = Path(expanded_pattern)
            is_abs = path_obj.is_absolute()
            if not is_abs:
                path_obj = Path(self.coder.root) / path_obj

            matches = []
            # Check for literal path existence first
            if path_obj.exists():
                matches = [path_obj]
            else:
                # If literal path doesn't exist, try globbing
                if is_abs:
                    # For absolute paths, glob it
                    matches = [Path(p) for p in glob.glob(expanded_pattern)]
                else:
                    # For relative paths and globs, use glob from the root directory
                    matches = list(Path(self.coder.root).glob(expanded_pattern))

            if not matches:
                self.io.tool_error(f"No matches found for: {pattern}")
            else:
                all_paths.extend(matches)

        # Then process them in sorted order
        for path in sorted(all_paths):
            abs_path = self.coder.abs_root_path(path)
            if os.path.isfile(abs_path):
                self._add_read_only_file(abs_path, path)
            elif os.path.isdir(abs_path):
                self._add_read_only_directory(abs_path, path)
            else:
                self.io.tool_error(f"Not a file or directory: {abs_path}")

    def _add_read_only_file(self, abs_path, original_name):
        if is_image_file(original_name) and not self.coder.main_model.info.get(
            "supports_vision"
        ):
            self.io.tool_error(
                f"Cannot add image file {original_name} as the"
                f" {self.coder.main_model.name} does not support images."
            )
            return

        if abs_path in self.coder.abs_read_only_fnames:
            self.io.tool_error(
                f"{original_name} is already in the chat as a read-only file"
            )
            return
        elif abs_path in self.coder.abs_fnames:
            self.coder.abs_fnames.remove(abs_path)
            self.coder.abs_read_only_fnames.add(abs_path)
            self.io.tool_output(
                f"Moved {original_name} from editable to read-only files in the chat"
            )
        else:
            self.coder.abs_read_only_fnames.add(abs_path)
            self.io.tool_output(f"Added {original_name} to read-only files.")

    def _add_read_only_directory(self, abs_path, original_name):
        added_files = 0
        for root, _, files in os.walk(abs_path):
            for file in files:
                file_path = os.path.join(root, file)
                if (
                    file_path not in self.coder.abs_fnames
                    and file_path not in self.coder.abs_read_only_fnames
                ):
                    self.coder.abs_read_only_fnames.add(file_path)
                    added_files += 1

        if added_files > 0:
            self.io.tool_output(
                f"Added {added_files} files from directory {original_name} to read-only files."
            )
        else:
            self.io.tool_output(f"No new files added from directory {original_name}.")

    def cmd_map(self, args):
        "Print out the current repository map"
        repo_map = self.coder.get_repo_map()
        if repo_map:
            self.io.tool_output(repo_map)
        else:
            self.io.tool_output("No repository map available.")

    def cmd_settings(self, args):
        "Print out the current settings"
        settings = format_settings(self.parser, self.args)
        announcements = "\n".join(self.coder.get_announcements())

        # Build metadata for the active models (main, editor, weak)
        model_sections = []
        active_models = [
            ("Main model", self.coder.main_model),
            ("Editor model", getattr(self.coder.main_model, "editor_model", None)),
            ("Weak model", getattr(self.coder.main_model, "weak_model", None)),
        ]
        for label, model in active_models:
            if not model:
                continue
            info = getattr(model, "info", {}) or {}
            if not info:
                continue
            model_sections.append(f"{label} ({model.name}):")
            for k, v in sorted(info.items()):
                model_sections.append(f"  {k}: {v}")
            model_sections.append("")  # blank line between models

        model_metadata = "\n".join(model_sections)

        output = f"{announcements}\n{settings}"
        if model_metadata:
            output += "\n" + model_metadata
        self.io.tool_output(output)

    def completions_raw_load(self, document, complete_event):
        return self.completions_raw_read_only(document, complete_event)

    def cmd_load(self, args):
        "Load and execute commands from a file"
        if not args.strip():
            self.io.tool_error("Please provide a filename containing commands to load.")
            return

        try:
            with open(
                args.strip(), "r", encoding=self.io.encoding, errors="replace"
            ) as f:
                commands = f.readlines()
        except FileNotFoundError:
            self.io.tool_error(f"File not found: {args}")
            return
        except Exception as e:
            self.io.tool_error(f"Error reading file: {e}")
            return

        for cmd in commands:
            cmd = cmd.strip()
            if not cmd or cmd.startswith("#"):
                continue

            self.io.tool_output(f"\nExecuting: {cmd}")
            try:
                self.run(cmd)
            except SwitchCoder:
                self.io.tool_error(
                    f"Command '{cmd}' is only supported in interactive mode, skipping."
                )

    def completions_raw_save(self, document, complete_event):
        return self.completions_raw_read_only(document, complete_event)

    def cmd_save(self, args):
        "Save commands to a file that can reconstruct the current chat session's files"
        if not args.strip():
            self.io.tool_error("Please provide a filename to save the commands to.")
            return

        try:
            with open(args.strip(), "w", encoding=self.io.encoding) as f:
                f.write("/drop\n")
                # Write commands to add editable files
                for fname in sorted(self.coder.abs_fnames):
                    rel_fname = self.coder.get_rel_fname(fname)
                    f.write(f"/add       {rel_fname}\n")

                # Write commands to add read-only files
                for fname in sorted(self.coder.abs_read_only_fnames):
                    # Use absolute path for files outside repo root, relative path for files inside
                    if Path(fname).is_relative_to(self.coder.root):
                        rel_fname = self.coder.get_rel_fname(fname)
                        f.write(f"/read-only {rel_fname}\n")
                    else:
                        f.write(f"/read-only {fname}\n")

            self.io.tool_output(f"Saved commands to {args.strip()}")
        except Exception as e:
            self.io.tool_error(f"Error saving commands to file: {e}")

    def cmd_multiline_mode(self, args):
        "Toggle multiline mode (swaps behavior of Enter and Meta+Enter)"
        self.io.toggle_multiline_mode()

    def cmd_copy(self, args):
        "Copy the last assistant message to the clipboard"
        all_messages = self.coder.done_messages + self.coder.cur_messages
        assistant_messages = [
            msg for msg in reversed(all_messages) if msg["role"] == "assistant"
        ]

        if not assistant_messages:
            self.io.tool_error("No assistant messages found to copy.")
            return

        last_assistant_message = assistant_messages[0]["content"]

        try:
            pyperclip.copy(last_assistant_message)
            preview = (
                last_assistant_message[:50] + "..."
                if len(last_assistant_message) > 50
                else last_assistant_message
            )
            self.io.tool_output(
                f"Copied last assistant message to clipboard. Preview: {preview}"
            )
        except pyperclip.PyperclipException as e:
            self.io.tool_error(f"Failed to copy to clipboard: {str(e)}")
            self.io.tool_output(
                "You may need to install xclip or xsel on Linux, or pbcopy on macOS."
            )
        except Exception as e:
            self.io.tool_error(
                f"An unexpected error occurred while copying to clipboard: {str(e)}"
            )

    def cmd_report(self, args):
        "Report a problem by opening a GitHub Issue"
        from lsr.report import report_github_issue

        announcements = "\n".join(self.coder.get_announcements())
        issue_text = announcements

        if args.strip():
            title = args.strip()
        else:
            title = None

        report_github_issue(issue_text, title=title, confirm=False)

    def cmd_editor(self, initial_content=""):
        "Open an editor to write a prompt"

        user_input = pipe_editor(initial_content, suffix="md", editor=self.editor)
        if user_input.strip():
            self.io.set_placeholder(user_input.rstrip())

    def _find_tex_files(self):
        """Find .tex files from the coder's tracked files or the working directory."""
        candidates = []

        # 1. From currently tracked files (abs_fnames + abs_read_only_fnames)
        for fpath in self.coder.abs_fnames | self.coder.abs_read_only_fnames:
            if fpath.endswith(".tex"):
                try:
                    candidates.append(self.coder.get_rel_fname(fpath))
                except Exception:
                    candidates.append(os.path.basename(fpath))

        # 2. From git tracked files
        if not candidates and self.coder.repo:
            try:
                for f in self.coder.repo.get_tracked_files():
                    if f.endswith(".tex"):
                        candidates.append(f)
            except Exception:
                pass

        # 3. From current working directory
        if not candidates:
            for f in os.listdir("."):
                if f.endswith(".tex") and not f.startswith("."):
                    candidates.append(f)

        return sorted(set(candidates))

    def _select_session_interactive(self, session_files):
        """Let the user interactively pick a session file (edit or note temp file).

        Returns the selected session file path, or None if cancelled.
        """
        import time

        # Sort newest first
        sorted_files = sorted(session_files, key=os.path.getmtime, reverse=True)

        self.io.tool_output(
            "\n\u001b[1m\u250c\u2500 Available sessions \u2500\u2510\u001b[0m"
        )
        for i, sf in enumerate(sorted_files, 1):
            mtime = os.path.getmtime(sf)
            time_str = time.strftime("%H:%M:%S", time.localtime(mtime))
            # Try to read session metadata for a richer display
            try:
                with open(sf, encoding="utf-8") as f:
                    session = json.load(f)
                original = os.path.basename(session.get("original_file", "unknown"))
                action = session.get("action", "edit")
                sections = len(session.get("sections", []))
                self.io.tool_output(
                    f"  {i}. \u001b[33m[{action}]\u001b[0m {original}"
                    f" ({sections} sections) \u2014 {time_str}"
                )
            except Exception:
                basename = os.path.basename(sf)
                self.io.tool_output(f"  {i}. {basename} \u2014 {time_str}")

        self.io.tool_output("  q. Cancel")
        sel = input("\nSelect session: ")
        if not sel or sel.lower() == "q":
            return None
        try:
            idx = int(sel) - 1
            return sorted_files[idx]
        except (ValueError, IndexError):
            self.io.tool_error("Invalid selection.")
            return None

    def _parse_and_select_sections(self, args, action_verb="edit"):
        """Parse a .tex file's LaTeX structure and let the user interactively select sections.

        Returns (abs_path, filename, items, selected_items) where:
          - abs_path: absolute path of the file
          - filename: the original filename string
          - items: full list of (sec_type, title, start_line, end_line, content)
          - selected_items: list of (sec_type, title, start_line, end_line, content) for user's selection
        Returns None if the user cancels or the file is invalid.
        """
        import re

        if not args:
            # Auto-sniff .tex files when no argument given
            candidates = self._find_tex_files()
            if len(candidates) == 1:
                args = candidates[0]
                self.io.tool_output(f"Auto-detected: {args}")
            elif len(candidates) > 1:
                self.io.tool_output(
                    "\n\u001b[1m\u250c\u2500 .tex files \u2500\u2510\u001b[0m"
                )
                for i, f in enumerate(candidates, 1):
                    self.io.tool_output(f"  {i}. {f}")
                self.io.tool_output("  q. Cancel")
                sel = input("\nSelect file: ")
                if not sel or sel.lower() == "q":
                    return None
                try:
                    idx = int(sel) - 1
                    args = candidates[idx]
                except (ValueError, IndexError):
                    self.io.tool_error("Invalid selection.")
                    return None
            else:
                self.io.tool_output(f"Usage: /{action_verb} <file.tex>")
                self.io.tool_output("")
                self.io.tool_output(
                    f"Interactively select LaTeX sections to {action_verb}."
                )
                return None

        filename = args.strip()
        abs_path = self.coder.abs_root_path(filename)

        if not os.path.exists(abs_path):
            self.io.tool_error(f"File not found: {filename}")
            return None

        try:
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.io.tool_error(f"Error reading file: {e}")
            return None

        # Parse LaTeX structure
        lines = content.split("\n")
        items = []

        section_pattern = re.compile(r"\\(section|subsection|subsubsection)\{([^}]+)\}")

        section_markers = []
        for i, line in enumerate(lines):
            m = section_pattern.search(line)
            if m:
                section_markers.append((i, m.group(1), m.group(2)))

        for idx, (start_line, sec_type, title) in enumerate(section_markers):
            if idx + 1 < len(section_markers):
                end_line = section_markers[idx + 1][0] - 1
            else:
                end_line = len(lines) - 1

            while end_line > start_line and not lines[end_line].strip():
                end_line -= 1

            section_content = "\n".join(lines[start_line : end_line + 1])
            items.append((sec_type, title, start_line, end_line, section_content))

        if not items:
            self.io.tool_output("No sections found in this file.")
            return None

        # Load persisted marks and edit counts for this file
        marks = self._load_marks()
        marked_titles = marks.get(abs_path, set())
        edit_counts_all = self._load_edit_counts()
        edit_counts = edit_counts_all.get(abs_path, {})

        # Display structure with per-section edit count and marked status
        self.io.tool_output(
            f"\n\u001b[1m\u250c\u2500 Structure of {filename} \u2500\u2510\u001b[0m"
        )
        for idx, (item_type, title, start, end, _) in enumerate(items, 1):
            indent = (
                "  "
                if item_type == "subsection"
                else ("    " if item_type == "subsubsection" else "")
            )
            icons = {
                "section": "\u001b[36m\u00a7\u001b[0m",
                "subsection": " \u00a7",
                "subsubsection": "  \u00a7",
            }
            icon = icons.get(item_type, "\u25a1")
            # Show ✓ in green for marked sections
            is_marked = title in marked_titles
            if is_marked:
                mark_prefix = "\u001b[32m\u2713\u001b[0m "
            else:
                mark_prefix = "  "
            # Show per-section edit count in yellow if > 0
            count = edit_counts.get(title, 0)
            count_str = f" \u001b[33m(×{count})\u001b[0m" if count > 0 else ""
            self.io.tool_output(
                f"  {idx:2d}. {mark_prefix}{icon} {indent}{title} [{start + 1}-{end + 1}]{count_str}"
            )

        self.io.tool_output(f"\nSelect sections to {action_verb}:")
        self.io.tool_output("  - Single: 1,3,5")
        self.io.tool_output("  - Range:  1-5")
        self.io.tool_output("  - All:    all")
        self.io.tool_output("  - Create: c")
        self.io.tool_output("  - Remove: r")
        self.io.tool_output("  - Move:   m")
        self.io.tool_output("  - Cancel: q")

        selection = input("\nSelection: ")

        if not selection or selection.lower() == "q":
            return None

        # ── Create section mode ──────────────────────────────
        if selection.lower() == "c":
            return self._create_section(abs_path, filename, lines, items)

        # ── Remove section mode ─────────────────────────────
        if selection.lower() == "r":
            return self._remove_section(abs_path, filename, lines, items)

        # ── Move section mode ───────────────────────────────
        if selection.lower() == "m":
            return self._move_section(abs_path, filename, lines, items)

        selected_indices = set()
        if selection.lower() == "all":
            selected_indices = set(range(len(items)))
        else:
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    try:
                        s, e = part.split("-")
                        for i in range(int(s) - 1, int(e)):
                            if 0 <= i < len(items):
                                selected_indices.add(i)
                    except ValueError:
                        pass
                else:
                    try:
                        idx = int(part) - 1
                        if 0 <= idx < len(items):
                            selected_indices.add(idx)
                    except ValueError:
                        pass

        if not selected_indices:
            self.io.tool_output("No valid selection.")
            return None

        selected_items = [items[i] for i in sorted(selected_indices)]
        return (abs_path, filename, items, selected_items)

    def _create_section(self, abs_path, filename, lines, items):
        """Interactive section/subsection/subsubsection creation.

        Flow: level → title → position → insert into file → re-invoke picker.
        """
        level_names = {
            "1": "section",
            "2": "subsection",
            "3": "subsubsection",
            "4": "paragraph",
        }

        # ── Step 1: Choose level ─────────────────────────────
        self.io.tool_output("\n\u001b[1mCreate new section\u001b[0m")
        self.io.tool_output("  1. section")
        self.io.tool_output("  2. subsection")
        self.io.tool_output("  3. subsubsection")
        self.io.tool_output("  4. paragraph")

        level_choice = input("\nLevel [1-4]: ").strip()
        if level_choice not in level_names:
            self.io.tool_error("Invalid level.")
            return None
        level_name = level_names[level_choice]
        latex_cmd = "\\" + level_name

        # ── Step 2: Enter title ──────────────────────────────
        title = input("Title: ").strip()
        if not title:
            self.io.tool_error("Empty title, cancelled.")
            return None

        # ── Step 3: Choose position ──────────────────────────
        self.io.tool_output(f"\nInsert \\{level_name}{{{title}}} at position:")
        self.io.tool_output("  - Before section 1, after section N, etc.")
        self.io.tool_output(f"  - Enter 1–{len(items)} to insert before that section")
        self.io.tool_output(f"  - Enter {len(items) + 1} or larger to append at end")

        pos_input = input(f"\nPosition [1-{len(items) + 1}]: ").strip()
        try:
            pos = int(pos_input)
        except ValueError:
            self.io.tool_error("Invalid position.")
            return None

        # Clamp to valid range
        pos = max(1, min(pos, len(items) + 1))

        # ── Step 4: Build the new section text ───────────────
        new_text = f"{latex_cmd}{{{title}}}"
        # Add a TODO placeholder body
        new_text += f"\n% TODO: Write {level_name} content here"

        # ── Step 5: Determine insertion line ──────────────────
        if pos <= len(items):
            # Insert before section at index (pos-1)
            insert_line = items[pos - 1][2]  # start_line of target
        else:
            # Append at end of file
            insert_line = len(lines)

        # ── Step 6: Insert into file ─────────────────────────
        new_lines = new_text.split("\n")
        # Add blank line separator before new section (unless at start)
        if insert_line > 0 and lines[insert_line - 1].strip():
            new_lines.insert(0, "")
        # Add blank line after
        new_lines.append("")

        lines[insert_line:insert_line] = new_lines

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self.io.tool_output(
            f"\n\u001b[32m\u2714 Created \\{level_name}{{{title}}} at position {pos}\u001b[0m"
        )

        # ── Step 7: Re-invoke the section picker ─────────────
        return self._parse_and_select_sections(filename, action_verb="edit")

    def _remove_section(self, abs_path, filename, lines, items):
        """Interactive section removal with double confirmation.

        Flow: select section → confirm → confirm again → delete → re-invoke picker.
        """
        self.io.tool_output(
            "\n\u001b[1m\u001b[31mRemove section\u001b[0m — select section to delete"
        )
        for i, (sec_type, title, *_rest) in enumerate(items, 1):
            self.io.tool_output(f"  {i}. \\{sec_type}{{{title}}}")

        idx_input = input(f"\nSection to remove [1-{len(items)}]: ").strip()
        try:
            idx = int(idx_input) - 1
            if not (0 <= idx < len(items)):
                raise ValueError
        except ValueError:
            self.io.tool_error("Invalid selection.")
            return None

        sec_type, title, start, end, content = items[idx]

        # First confirmation
        self.io.tool_output(
            f"\n\u001b[33m\u26a0 About to delete \\{sec_type}{{{title}}} "
            f"(lines {start + 1}–{end + 1}, {end - start + 1} lines)\u001b[0m"
        )
        confirm1 = input("Type 'yes' to confirm: ").strip().lower()
        if confirm1 != "yes":
            self.io.tool_output("Cancelled.")
            return self._parse_and_select_sections(filename, action_verb="edit")

        # Second confirmation
        self.io.tool_output(
            "\n\u001b[31m\u26a0 FINAL WARNING: This cannot be undone.\u001b[0m"
        )
        self.io.tool_output(
            f"  Deleting \\{sec_type}{{{title}}} permanently."
        )
        confirm2 = input("Type 'DELETE' to proceed: ").strip()
        if confirm2 != "DELETE":
            self.io.tool_output("Cancelled.")
            return self._parse_and_select_sections(filename, action_verb="edit")

        # Remove lines from file
        # Also remove blank lines before the section (separator)
        rm_start = start
        while rm_start > 0 and not lines[rm_start - 1].strip():
            rm_start -= 1
        # And blank lines after
        rm_end = end
        while rm_end < len(lines) - 1 and not lines[rm_end + 1].strip():
            rm_end += 1

        del lines[rm_start : rm_end + 1]

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self.io.tool_output(
            f"\n\u001b[32m\u2714 Removed \\{sec_type}{{{title}}}\u001b[0m"
        )

        return self._parse_and_select_sections(filename, action_verb="edit")

    def _move_section(self, abs_path, filename, lines, items):
        """Interactive section reordering.

        Flow: select section → choose target position → move → re-invoke picker.
        """
        self.io.tool_output(
            "\n\u001b[1mMove section\u001b[0m — select section and target position"
        )
        for i, (sec_type, title, *_rest) in enumerate(items, 1):
            self.io.tool_output(f"  {i}. \\{sec_type}{{{title}}}")

        src_input = input(f"\nSection to move [1-{len(items)}]: ").strip()
        try:
            src_idx = int(src_input) - 1
            if not (0 <= src_idx < len(items)):
                raise ValueError
        except ValueError:
            self.io.tool_output("Invalid selection.")
            return None

        src_type, src_title, src_start, src_end, src_content = items[src_idx]

        self.io.tool_output(
            f"\nMove \\{src_type}{{{src_title}}} before which section?"
        )
        # Re-list with current positions (excluding the moving section)
        display_idx = 0
        target_map = {}  # display_idx → actual position in file
        for i, (sec_type, title, *_rest) in enumerate(items):
            if i == src_idx:
                continue
            display_idx += 1
            target_map[display_idx] = i
            self.io.tool_output(f"  {display_idx}. \\{sec_type}{{{title}}}")
        # Option to append at end
        display_idx += 1
        target_map[display_idx] = len(items)  # sentinel: append
        self.io.tool_output(f"  {display_idx}. (end of file)")

        tgt_input = input(f"\nInsert before [1-{display_idx}]: ").strip()
        try:
            tgt_display = int(tgt_input)
            if not (1 <= tgt_display <= display_idx):
                raise ValueError
        except ValueError:
            self.io.tool_output("Invalid target.")
            return None

        # Determine actual target index in items[]
        tgt_idx = target_map[tgt_display]

        if tgt_idx == src_idx or (src_idx + 1 == tgt_idx):
            # Moving to same position — no-op
            self.io.tool_output("Already in that position.")
            return self._parse_and_select_sections(filename, action_verb="edit")

        # ── Perform the move on lines[] ─────────────────────
        # Extract section block (with surrounding blank lines)
        rm_start = src_start
        while rm_start > 0 and not lines[rm_start - 1].strip():
            rm_start -= 1
        rm_end = src_end
        while rm_end < len(lines) - 1 and not lines[rm_end + 1].strip():
            rm_end += 1

        block = lines[rm_start : rm_end + 1]
        del lines[rm_start : rm_end + 1]

        # Now line numbers have shifted — recalculate target position
        # Build remaining items list (after removing src)
        remaining = [it for j, it in enumerate(items) if j != src_idx]

        if tgt_idx < len(remaining):
            # Insert before remaining[tgt_idx]
            # Search for the target heading in modified lines[]
            tgt_item = remaining[tgt_idx]
            target_heading = f"\\{tgt_item[0]}{{{tgt_item[1]}}}"
            insert_at = None
            for i, ln in enumerate(lines):
                if target_heading in ln:
                    insert_at = i
                    break
            if insert_at is None:
                insert_at = len(lines)
        else:
            insert_at = len(lines)

        # Add blank line before if needed
        if insert_at > 0 and lines[insert_at - 1].strip():
            block.insert(0, "")
        block.append("")
        lines[insert_at:insert_at] = block

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self.io.tool_output(
            f"\n\u001b[32m\u2714 Moved \\{src_type}{{{src_title}}} to new position\u001b[0m"
        )

        return self._parse_and_select_sections(filename, action_verb="edit")

    @staticmethod
    def _sanitize_filename(title):
        """Format a LaTeX section title into a safe filename fragment.

        - Lowercase
        - Strip LaTeX commands (e.g. ``\\textbf{foo}`` → ``foo``)
        - Spaces → underscores
        - Remove non-alphanumeric/underscore chars
        - Truncate to 40 chars
        """
        # Strip LaTeX commands: \cmd{content} → content
        title = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", title)
        # Strip any remaining backslash-commands
        title = re.sub(r"\\[a-zA-Z]+", "", title)
        # Lowercase & spaces → underscores
        title = title.lower().replace(" ", "_")
        # Keep only alphanumeric + underscore
        title = re.sub(r"[^a-z0-9_]", "", title)
        # Collapse multiple underscores
        title = re.sub(r"_+", "_", title)
        # Strip leading/trailing underscores
        title = title.strip("_")
        # Truncate
        return title[:40]

    def _marks_file(self):
        """Return path to the persistent marks JSON file."""
        return os.path.join(os.path.expanduser("~"), ".lsr", "marks.json")

    def _edit_counts_file(self):
        """Return path to the persistent edit-counts JSON file."""
        return os.path.join(os.path.expanduser("~"), ".lsr", "edit_counts.json")

    def _load_marks(self):
        """Load persisted marks from ~/.lsr/marks.json.

        Returns dict mapping abs_file_path → set of section titles.
        """
        path = self._marks_file()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return {k: set(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_marks(self, marks):
        """Persist marks dict to ~/.lsr/marks.json."""
        path = self._marks_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        serializable = {k: sorted(v) for k, v in marks.items() if v}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)

    def _load_edit_counts(self):
        """Load persisted per-section edit counts from ~/.lsr/edit_counts.json.

        Returns dict mapping abs_file_path → {section_title: count}.
        """
        path = self._edit_counts_file()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return {k: dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_edit_counts(self, counts):
        """Persist edit counts dict to ~/.lsr/edit_counts.json."""
        path = self._edit_counts_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(counts, f, indent=2, ensure_ascii=False)

    def _increment_edit_counts(self, abs_path, selected_items):
        """Increment edit count for each selected section and persist."""
        counts = self._load_edit_counts()
        if abs_path not in counts:
            counts[abs_path] = {}
        for _, title, _, _, _ in selected_items:
            counts[abs_path][title] = counts[abs_path].get(title, 0) + 1
        self._save_edit_counts(counts)
        return counts.get(abs_path, {})

    def cmd_edit(self, args=""):
        """Edit LaTeX sections with hash-based tracking and auto-replacement."""
        import hashlib

        result = self._parse_and_select_sections(args, action_verb="edit")
        if result is None:
            return

        abs_path, filename, items, selected_items = result

        # Increment per-section edit counts and persist
        file_counts = self._increment_edit_counts(abs_path, selected_items)
        self._last_edit_file = abs_path

        # Build session data (original content + line numbers)
        session_data = {
            "original_file": abs_path,
            "sections": [],
        }

        tmp_content = []
        tmp_content.append("% LSR Edit File")
        tmp_content.append("% Edit the sections below, then run /edit-done")
        tmp_content.append("")

        # Collect titles for filename construction
        section_titles = []

        for item_type, title, start, end, item_content in selected_items:
            h = hashlib.sha256(item_content.encode()).hexdigest()[:8]
            section_titles.append(title)

            # Save to session
            session_data["sections"].append(
                {
                    "hash": h,
                    "type": item_type,
                    "title": title,
                    "start_line": start,
                    "end_line": end,
                    "original_content": item_content,
                }
            )

            # Write to temp file
            tmp_content.append(f"% === {item_type}: {title} (hash: {h}) ===")
            tmp_content.append(item_content)
            tmp_content.append("")

        # Build descriptive filename from first 2 section titles + hash
        # e.g. lsr_edit_introduction__methodology_a3f2b1c0.tex
        name_parts = []
        for t in section_titles[:2]:
            sanitized = self._sanitize_filename(t)
            if sanitized:
                name_parts.append(sanitized)
        descriptive = "__".join(name_parts) if name_parts else "section"
        # Hash for deduplication from all section contents
        all_content = "\n".join(
            item_content for _, _, _, _, item_content in selected_items
        )
        dedup_hash = hashlib.sha256(all_content.encode()).hexdigest()[:8]

        # Store temp file in ~/.lsr/tmp/
        lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")
        os.makedirs(lsr_home, exist_ok=True)
        tmp_filename = f"lsr_edit_{descriptive}_{dedup_hash}.tex"
        tmp_path = os.path.join(lsr_home, tmp_filename)
        tmp_path = os.path.abspath(tmp_path)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(tmp_content))

        # Save session file
        session_file = tmp_path + ".session"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

        # Add temp file to coder's editable list
        self.coder.abs_fnames.add(tmp_path)

        # Show summary with per-section edit counts
        self.io.tool_output("\n\u001b[32m\u2714 Ready to edit!\u001b[0m")
        for _, title, _, _, _ in selected_items:
            c = file_counts.get(title, 0)
            self.io.tool_output(f"  \u001b[33m×{c}\u001b[0m {title}")
        self.io.tool_output(f"\u001b[36m\u250c\u2500 Edit file:\u001b[0m {tmp_path}")
        self.io.tool_output(f"\u001b[36m\u2514\u2500 Original:\u001b[0m   {filename}")
        self.io.tool_output("\nNext steps:")
        self.io.tool_output("  1. Ask LLM to edit the sections")
        self.io.tool_output("  2. Run /edit-done to merge changes back")

    def _merge_sections_from_session(self, session_file):
        """Merge sections from a session file back to the original file.

        Shared logic for /edit-done, /expand-done, /translate-done, /condense-done.
        """
        import json
        import re

        with open(session_file, encoding="utf-8") as f:
            session = json.load(f)

        original_file = session["original_file"]
        tmp_file = session_file.replace(".session", "")

        if not os.path.exists(tmp_file):
            self.io.tool_error(f"Preview file not found: {tmp_file}")
            return

        # Read edited temp file
        with open(tmp_file, encoding="utf-8") as f:
            edited_content = f.read()

        # Parse edited content by hash
        hash_pattern = re.compile(r"% === (?:.*?):.*?\(hash: (\w+)\) ===")
        edited_sections = {}
        current_hash = None
        current_lines = []

        for line in edited_content.split("\n"):
            m = hash_pattern.search(line)
            if m:
                if current_hash and current_lines:
                    while current_lines and not current_lines[-1].strip():
                        current_lines.pop()
                    edited_sections[current_hash] = "\n".join(current_lines)
                current_hash = m.group(1)
                current_lines = []
            elif current_hash:
                current_lines.append(line)

        if current_hash and current_lines:
            while current_lines and not current_lines[-1].strip():
                current_lines.pop()
            edited_sections[current_hash] = "\n".join(current_lines)

        # Read original file
        with open(original_file, encoding="utf-8") as f:
            original_lines = f.read().split("\n")

        # Replace sections from bottom to top (to preserve line numbers)
        sections = sorted(
            session["sections"], key=lambda s: s["start_line"], reverse=True
        )

        replaced_count = 0
        for section in sections:
            h = section["hash"]
            start = section["start_line"]
            end = section["end_line"]

            if h in edited_sections:
                new_content = edited_sections[h]
                new_lines = new_content.split("\n")
                original_lines[start : end + 1] = new_lines
                replaced_count += 1

        # Write back to original file
        with open(original_file, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        # Remove temp file and session
        try:
            os.remove(tmp_file)
            os.remove(session_file)
        except Exception:
            pass

        # Remove from coder's editable files
        if tmp_file in self.coder.abs_fnames:
            self.coder.abs_fnames.remove(tmp_file)

        action = session.get("action", "edit")
        self.io.tool_output(
            f"\n\u001b[32m\u2714 Merged {replaced_count} section(s) back to:\u001b[0m"
        )
        self.io.tool_output(f"   {original_file}")

    def _done_command(self, action_verb):
        """Shared merge-back logic for /{action}-done commands."""
        import glob

        lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")
        pattern = os.path.join(lsr_home, f"lsr_{action_verb}_*.tex.session")
        session_files = glob.glob(pattern)

        if not session_files:
            self.io.tool_error(
                f"No {action_verb} session found. Use /{action_verb} first."
            )
            return

        session_file = max(session_files, key=os.path.getmtime)
        self._merge_sections_from_session(session_file)

    def cmd_edit_done(self, args=""):
        """Merge edited sections back to original file."""
        import glob

        lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")
        session_files = glob.glob(os.path.join(lsr_home, "lsr_edit_*.tex.session"))

        if not session_files:
            self.io.tool_error("No edit session found. Use /edit first.")
            return

        session_file = max(session_files, key=os.path.getmtime)
        self._merge_sections_from_session(session_file)

    def cmd_expand_done(self, args=""):
        "Deprecated: use /edit-done instead."
        self.io.tool_output(
            "\033[33m/expand-done is deprecated. Use /edit-done instead.\033[0m"
        )
        return self.cmd_edit_done(args)

    def cmd_translate_done(self, args=""):
        "Deprecated: use /edit-done instead."
        self.io.tool_output(
            "\033[33m/translate-done is deprecated. Use /edit-done instead.\033[0m"
        )
        return self.cmd_edit_done(args)

    def cmd_condense_done(self, args=""):
        "Deprecated: use /edit-done instead."
        self.io.tool_output(
            "\033[33m/condense-done is deprecated. Use /edit-done instead.\033[0m"
        )
        return self.cmd_edit_done(args)

    def cmd_note_done(self, args=""):
        "Deprecated: use /edit-done instead."
        self.io.tool_output(
            "\u001b[33m/note-done is deprecated. Use /edit-done instead.\u001b[0m"
        )
        return self.cmd_edit_done(args)

    def cmd_renote(self, args=""):
        """Deprecated: use /note instead. /note now handles both new and existing sessions."""
        self.io.tool_output(
            "\u001b[33m/renote is deprecated. Use /note instead.\u001b[0m"
            "\n  /note          — list existing sessions and render in browser"
            "\n  /note <file>   — select sections from a .tex file to review"
        )
        return self.cmd_note(args)

    def cmd_mark(self, args=""):
        """Mark LaTeX sections as completed (persisted across sessions).

        Usage:
            /mark <file.tex>          Interactively select sections to mark as done
            /mark --reset <file.tex>   Interactively select sections to unmark
            /mark --reset              Clear ALL marks across all files
        """
        args = args.strip()

        # Handle --reset variants
        if args.startswith("--reset"):
            rest = args[7:].strip()  # everything after '--reset'
            marks = self._load_marks()

            if rest:
                # /mark --reset <file.tex> — interactive unmark
                filename = rest
                abs_path = self.coder.abs_root_path(filename)

                # Check if file has any marks
                if abs_path not in marks or not marks[abs_path]:
                    self.io.tool_output(f"No marks found for {filename}")
                    return

                # Use interactive selection for unmarking
                result = self._parse_and_select_sections(rest, action_verb="unmark")
                if result is None:
                    return

                abs_path, filename, items, selected_items = result

                # Remove selected sections from marks
                if abs_path in marks:
                    unmarked_names = []
                    for _, title, _, _, _ in selected_items:
                        if title in marks[abs_path]:
                            marks[abs_path].discard(title)
                            unmarked_names.append(title)

                    # Clean up empty entries
                    if not marks[abs_path]:
                        del marks[abs_path]
                    self._save_marks(marks)

                    # Also reset edit counts for unmarked sections
                    counts = self._load_edit_counts()
                    if abs_path in counts:
                        for title in unmarked_names:
                            counts[abs_path].pop(title, None)
                        if not counts[abs_path]:
                            del counts[abs_path]
                        self._save_edit_counts(counts)

                    # Show what was unmarked
                    self.io.tool_output(
                        f"\n\u001b[32m\u2714 Unmarked {len(unmarked_names)} section(s) in {filename}:\u001b[0m"
                    )
                    for t in unmarked_names:
                        self.io.tool_output(f"  \u001b[31m\u2717\u001b[0m {t}")
                else:
                    self.io.tool_output(f"No marks found for {filename}")
            else:
                # /mark --reset (clear all) — ask for confirmation
                total_marks = sum(len(v) for v in marks.values())
                if total_marks == 0:
                    self.io.tool_output("No marks to clear.")
                    return

                file_count = len(marks)
                self.io.tool_output(
                    f"\nThis will clear {total_marks} mark(s) across {file_count} file(s)."
                )
                confirm = input("Are you sure? (y/N): ")

                if confirm.lower() == "y":
                    self._save_marks({})
                    self._save_edit_counts({})
                    self.io.tool_output(
                        "\n\u001b[32m\u2714 Cleared ALL marks across all files\u001b[0m"
                    )
                else:
                    self.io.tool_output("Cancelled.")
            return

        # /mark <file.tex> — interactive selection (same UI as /edit)
        if not args:
            self.io.tool_output("Usage:")
            self.io.tool_output(
                "  /mark <file.tex>          Interactively mark sections as done"
            )
            self.io.tool_output(
                "  /mark --reset <file.tex>  Interactively unmark sections"
            )
            self.io.tool_output(
                "  /mark --reset            Clear ALL marks (with confirmation)"
            )

            # Show current marks summary
            marks = self._load_marks()
            if marks:
                self.io.tool_output("\nCurrent marks:")
                for fpath, titles in sorted(marks.items()):
                    fname = os.path.basename(fpath)
                    self.io.tool_output(f"  {fname}: {len(titles)} section(s)")
            return

        result = self._parse_and_select_sections(args, action_verb="mark")
        if result is None:
            return

        abs_path, filename, items, selected_items = result

        # Load, update, and save marks
        marks = self._load_marks()
        if abs_path not in marks:
            marks[abs_path] = set()
        for _, title, _, _, _ in selected_items:
            marks[abs_path].add(title)
        self._save_marks(marks)

        # Reset edit counts for marked sections
        counts = self._load_edit_counts()
        if abs_path in counts:
            for _, title, _, _, _ in selected_items:
                counts[abs_path].pop(title, None)
            if not counts[abs_path]:
                del counts[abs_path]
            self._save_edit_counts(counts)

        # Show what was marked
        marked_names = [title for _, title, _, _, _ in selected_items]
        self.io.tool_output(
            f"\n\u001b[32m\u2714 Marked {len(marked_names)} section(s) as done in {filename}:\u001b[0m"
        )
        for t in marked_names:
            self.io.tool_output(f"  \u001b[32m\u2713\u001b[0m {t}")
        self.io.tool_output("Edit counts reset for marked sections.")

    def _run_section_command(self, args, action_verb, prompt_template):
        """Shared implementation for /expand, /condense, /translate commands.

        Selects sections, writes them to a temp file with hash markers,
        saves a session file, then sends the LLM to edit the temp file.
        User reviews with /{action_verb}-done to merge back.
        """
        import hashlib

        result = self._parse_and_select_sections(args, action_verb=action_verb)
        if result is None:
            return

        abs_path, filename, items, selected_items = result

        # Build session data and temp file content
        session_data = {
            "action": action_verb,
            "original_file": abs_path,
            "sections": [],
        }

        tmp_content = [
            f"% LSR {action_verb.capitalize()} File",
            "% The sections below will be edited. Run /edit-done to apply.",
            "",
        ]

        section_titles = []
        for item_type, title, start, end, item_content in selected_items:
            h = hashlib.sha256(item_content.encode()).hexdigest()[:8]
            section_titles.append(title)

            session_data["sections"].append(
                {
                    "hash": h,
                    "type": item_type,
                    "title": title,
                    "start_line": start,
                    "end_line": end,
                    "original_content": item_content,
                }
            )

            tmp_content.append(f"% === {item_type}: {title} (hash: {h}) ===")
            tmp_content.append(item_content)
            tmp_content.append("")

        # Build descriptive filename
        name_parts = []
        for t in section_titles[:2]:
            sanitized = self._sanitize_filename(t)
            if sanitized:
                name_parts.append(sanitized)
        descriptive = "__".join(name_parts) if name_parts else "section"
        all_content = "\n".join(
            item_content for _, _, _, _, item_content in selected_items
        )
        dedup_hash = hashlib.sha256(all_content.encode()).hexdigest()[:8]

        # Write temp file to ~/.lsr/tmp/
        lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")
        os.makedirs(lsr_home, exist_ok=True)
        tmp_filename = f"lsr_edit_{descriptive}_{dedup_hash}.tex"
        tmp_path = os.path.join(lsr_home, tmp_filename)
        tmp_path = os.path.abspath(tmp_path)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(tmp_content))

        # Save session file
        session_file = tmp_path + ".session"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

        # Add temp file to coder's editable list
        self.coder.abs_fnames.add(tmp_path)

        # Build prompt from selected content
        combined_sections = []
        for item_type, title, start, end, item_content in selected_items:
            combined_sections.append(
                f"% --- {item_type}: {title} (lines {start + 1}-{end + 1}) ---\n"
                f"{item_content}"
            )
        combined_content = "\n\n".join(combined_sections)
        user_msg = prompt_template.format(content=combined_content)

        # Inform the user
        section_count = len(selected_items)
        self.io.tool_output(
            f"\n\u001b[32m\u2714 {action_verb.capitalize()}ing {section_count} "
            f"section(s) from {filename}...\u001b[0m"
        )

        # Send LLM to edit the temp file (not the original)
        return self._generic_chat_command_for_file(
            tmp_path, user_msg, self.coder.main_model.edit_format
        )

    def cmd_deai(self, args=""):
        "Remove AI writing patterns from LaTeX sections (iterative self-audit)"
        return self._run_section_command(args, "deai", prompts.deai_prompt)

    def cmd_expand(self, args=""):
        "Expand LaTeX sections with richer scientific detail"
        return self._run_section_command(args, "expand", prompts.expand_prompt)

    def cmd_condense(self, args=""):
        "Condense LaTeX sections while preserving essential scientific content"
        return self._run_section_command(args, "condense", prompts.condense_prompt)

    def cmd_translate(self, args=""):
        "Translate LaTeX sections from Chinese to English (academic style)"
        return self._run_section_command(args, "translate", prompts.translate_prompt)

    def _extract_paragraphs_from_temp(self, content):
        """Parse paragraphs from a temp file's content (edit or note session).

        The temp file uses `% === type: title (hash: xxx) ===` markers to
        delimit sections.  This method extracts text environments from each
        section for HTML rendering.

        Returns a list of (section_title, env_name, text) tuples suitable
        for generate_note_html().
        """
        from lsr.latex_tools import extract_text_environments

        hash_pattern = re.compile(r"% === (.*?): (.*?) \(hash: (\w+)\) ===")
        current_section = None
        current_lines = []
        paragraphs = []

        for line in content.split("\n"):
            m = hash_pattern.search(line)
            if m:
                if current_section and current_lines:
                    section_content = "\n".join(current_lines)
                    paras = extract_text_environments(
                        [(current_section, current_section, 0, 0, section_content)]
                    )
                    paragraphs.extend(paras)
                current_section = m.group(2)
                current_lines = []
            elif current_section and not line.startswith("%"):
                current_lines.append(line)

        if current_section and current_lines:
            section_content = "\n".join(current_lines)
            paras = extract_text_environments(
                [(current_section, current_section, 0, 0, section_content)]
            )
            paragraphs.extend(paras)

        return paragraphs

    def _render_session_as_html(self, session_file):
        """Render a session's temp file as HTML in the browser and process comments.

        Shared by /note (no-args existing-session path) and /renote.
        Opens the browser, waits for comments, then sends LLM edits.
        """
        import webbrowser

        from lsr.note_html import generate_note_html
        from lsr.note_server import NoteServer

        with open(session_file, encoding="utf-8") as f:
            session = json.load(f)

        tmp_file = session_file.replace(".session", "")
        if not os.path.exists(tmp_file):
            self.io.tool_error(f"Preview file not found: {tmp_file}")
            return

        original_file = session.get("original_file", "unknown.tex")
        filename = os.path.basename(original_file)

        # Read temp file and extract paragraphs for HTML
        with open(tmp_file, encoding="utf-8") as f:
            content = f.read()

        paragraphs = self._extract_paragraphs_from_temp(content)
        if not paragraphs:
            self.io.tool_error("No text content found in temp file.")
            return

        # Generate HTML and start server
        html_path = generate_note_html(filename, paragraphs, port=0)
        server = NoteServer(html_path)
        server.start()

        # Re-generate with actual port
        html_path = generate_note_html(filename, paragraphs, port=server.port)
        server.html_path = html_path

        url = f"http://localhost:{server.port}"
        self.io.tool_output("\n\u001b[32m\u2714 Opening note review...\u001b[0m")
        self.io.tool_output(f"URL: {url}")
        webbrowser.open(url)

        # Wait for response (approve/cancel)
        comments = server.wait_for_response(timeout=300)

        if comments is None:
            self.io.tool_output("Note cancelled or timed out.")
            return

        comment_list = comments.get("comments", [])
        if not comment_list:
            self.io.tool_output("No comments to process.")
            return

        user_msg = self._format_note_prompt(comments)
        self.io.tool_output(f"\nProcessing {len(comment_list)} comment(s)...")
        self.io.tool_output("\nNext steps:")
        self.io.tool_output("  1. LLM will edit the preview file")
        self.io.tool_output("  2. Run /note-done to merge changes back")
        return self._generic_chat_command_for_file(
            tmp_file, user_msg, self.coder.main_model.edit_format
        )

    def _get_chat_files(self):
        """Return (editable_files, read_only_files) currently in the chat session."""
        editable_files = list(self.coder.get_inchat_relative_files())
        read_only_files = [
            self.coder.get_rel_fname(fn) for fn in self.coder.abs_read_only_fnames
        ]
        return editable_files, read_only_files

    def _select_file_interactive(self, all_files, header="Files in chat"):
        """List files and let the user pick one. Returns rel_fname or None."""
        self.io.tool_output(f"\n\u001b[1m\u250c\u2500 {header} \u2500\u2510\u001b[0m")
        for idx, f in enumerate(all_files, 1):
            self.io.tool_output(f"  {idx}. {f}")

        self.io.tool_output("  q. Cancel")
        sel = input("\nSelect file: ").strip()
        if not sel or sel.lower() == "q":
            return None
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(all_files):
                return all_files[idx]
        except ValueError:
            pass
        self.io.tool_error("Invalid selection.")
        return None

    def cmd_note(self, args=""):
        """Review LaTeX file in browser with highlight and comments.

        When called without arguments (like /open):
          Lists files currently in the chat session.
          - If the selected file is an edit temp file → renders it as HTML.
          - If the selected file is a regular .tex → section selection → create temp → render.
          If no files in chat, auto-triggers /edit (tex sniffing + section selection).
        When called with <file.tex>:
          Directly selects sections from that file → creates temp file → render HTML.
        All temp files use /edit-done to merge back.
        """
        import hashlib
        import webbrowser

        from lsr.latex_tools import extract_text_environments
        from lsr.note_html import generate_note_html
        from lsr.note_server import NoteServer

        # --- No args: list files currently in chat (like /open) ---
        if not args.strip():
            editable_files, read_only_files = self._get_chat_files()
            all_files = editable_files + read_only_files

            if all_files:
                # Interactive selection (like /open)
                selected = self._select_file_interactive(
                    all_files, header="Files in chat"
                )
                if selected is None:
                    return

                # Check if selected file is a temp file with .session
                abs_path = self.coder.abs_root_path(selected)
                session_file = abs_path + ".session"
                if os.path.exists(session_file):
                    return self._render_session_as_html(session_file)

                # Regular .tex → fall through to section selection with this file
                args = selected
            else:
                # No files in chat → auto-trigger /edit flow
                self.io.tool_output(
                    "\nNo files in chat. Select sections to create an edit session..."
                )
                # _parse_and_select_sections supports tex auto-sniffing when args is empty

        # --- Section selection + temp file creation + HTML rendering ---
        result = self._parse_and_select_sections(args, action_verb="note")
        if result is None:
            return

        abs_path, filename, items, selected_items = result

        # Build session data
        session_data = {
            "action": "note",
            "original_file": abs_path,
            "sections": [],
        }

        tmp_content = [
            "% LSR Edit File (created by /note)",
            "% Review and add comments in the browser, then run /edit-done to apply.",
            "",
        ]

        section_titles = []
        for item_type, title, start, end, item_content in selected_items:
            h = hashlib.sha256(item_content.encode()).hexdigest()[:8]
            section_titles.append(title)

            session_data["sections"].append(
                {
                    "hash": h,
                    "type": item_type,
                    "title": title,
                    "start_line": start,
                    "end_line": end,
                    "original_content": item_content,
                }
            )

            tmp_content.append(f"% === {item_type}: {title} (hash: {h}) ===")
            tmp_content.append(item_content)
            tmp_content.append("")

        # Build descriptive filename
        name_parts = []
        for t in section_titles[:2]:
            sanitized = self._sanitize_filename(t)
            if sanitized:
                name_parts.append(sanitized)
        descriptive = "__".join(name_parts) if name_parts else "section"
        all_content = "\n".join(
            item_content for _, _, _, _, item_content in selected_items
        )
        dedup_hash = hashlib.sha256(all_content.encode()).hexdigest()[:8]

        # Write temp file (use lsr_edit_ prefix so /edit-done can find it)
        lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")
        os.makedirs(lsr_home, exist_ok=True)
        tmp_filename = f"lsr_edit_{descriptive}_{dedup_hash}.tex"
        tmp_path = os.path.join(lsr_home, tmp_filename)
        tmp_path = os.path.abspath(tmp_path)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(tmp_content))

        # Save session file
        session_file = tmp_path + ".session"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

        # Add temp file to coder's editable list
        self.coder.abs_fnames.add(tmp_path)

        # Extract text environments for HTML preview
        paragraphs = extract_text_environments(selected_items)
        if not paragraphs:
            self.io.tool_error("No text content found in selected sections.")
            return

        # Generate HTML, start server, open browser
        html_path = generate_note_html(filename, paragraphs, port=0)
        server = NoteServer(html_path)
        server.start()
        html_path = generate_note_html(filename, paragraphs, port=server.port)
        server.html_path = html_path

        url = f"http://localhost:{server.port}"
        self.io.tool_output("\n\u001b[32m\u2714 Note review ready!\u001b[0m")
        self.io.tool_output(f"\u001b[36m\u250c\u2500 Preview file:\u001b[0m {tmp_path}")
        self.io.tool_output(f"\u001b[36m\u2514\u2500 Original:\u001b[0m     {filename}")
        self.io.tool_output(f"\nOpening browser at {url}")
        self.io.tool_output("Add comments in the browser, then click Approve.")
        webbrowser.open(url)

        # Wait for response
        comments = server.wait_for_response(timeout=300)
        if comments is None:
            self.io.tool_output("Note cancelled or timed out.")
            return

        comment_list = comments.get("comments", [])
        if not comment_list:
            self.io.tool_output("No comments to process.")
            return

        user_msg = self._format_note_prompt(comments)
        self.io.tool_output(f"\nProcessing {len(comment_list)} comment(s)...")
        self.io.tool_output("\nNext steps:")
        self.io.tool_output("  1. LLM will edit the preview file")
        self.io.tool_output("  2. Run /edit-done to merge changes back")

        return self._generic_chat_command_for_file(
            tmp_path, user_msg, self.coder.main_model.edit_format
        )

    def completions_note(self):
        """Provide .tex file completions for /note command."""
        return self.completions_edit()

    def completions_renote(self):
        """Completions for /renote (deprecated alias for /note)."""
        return []

    def _format_note_prompt(self, comments):
        """Format note comments into an LLM prompt.

        The LLM will see this prompt along with the temp file content.
        We include the highlighted text so the LLM can locate the right paragraph.
        """
        lines = [
            "Please revise the following LaTeX paragraphs based on review comments.",
            "The file content is in the chat context. Find each paragraph by matching the quoted text below, then apply the suggested changes.\n",
        ]

        for i, comment in enumerate(comments.get("comments", []), 1):
            section = comment.get("section", "Unknown")
            highlight = comment.get("highlight", "")
            text = comment.get("text", "")

            lines.append(f"### Comment {i} — Section: {section}")
            if highlight:
                # Show first 150 chars of the highlighted text so LLM can locate it
                lines.append("Find this text:")
                lines.append(
                    f"> {highlight[:150]}{'...' if len(highlight) > 150 else ''}"
                )
            lines.append(f"Change requested: {text}")
            lines.append("")

        lines.append(
            "Please use SEARCH/REPLACE blocks to modify only the paragraphs with comments. "
            "Maintain academic style, LaTeX formatting, and math formulas."
        )
        return "\n".join(lines)

    def cmd_open(self, args=""):
        "Open a file in neovim in a new terminal window"
        import shutil

        # Get all added files
        editable_files = list(self.coder.get_inchat_relative_files())
        read_only_files = [
            self.coder.get_rel_fname(fn) for fn in self.coder.abs_read_only_fnames
        ]
        all_files = editable_files + read_only_files

        if not all_files:
            self.io.tool_output(
                "No files in chat. Starting /edit to select sections..."
            )
            return self.cmd_edit("")

        if args.strip():
            # Direct file name provided
            filename = args.strip()
            abs_path = self.coder.abs_root_path(filename)
            if not os.path.exists(abs_path):
                # Try substring match
                matches = [f for f in all_files if filename in f]
                if len(matches) == 1:
                    abs_path = self.coder.abs_root_path(matches[0])
                elif len(matches) > 1:
                    self.io.tool_error(f"Multiple matches: {matches}")
                    return
                else:
                    self.io.tool_error(f"File not found: {filename}")
                    return
        else:
            # Interactive selection
            self.io.tool_output("\n\u001b[1mFiles in chat:\u001b[0m")
            for idx, f in enumerate(all_files, 1):
                self.io.tool_output(f"  {idx}. {f}")

            self.io.tool_output("\nSelect file to open (or q to cancel):")

            selection = input("Selection: ").strip()
            if not selection or selection.lower() == "q":
                return

            try:
                idx = int(selection) - 1
                if 0 <= idx < len(all_files):
                    abs_path = self.coder.abs_root_path(all_files[idx])
                else:
                    self.io.tool_error("Invalid selection.")
                    return
            except ValueError:
                self.io.tool_error("Invalid input. Enter a number.")
                return

        # Find editor: prefer code (VS Code), then nvim/vim
        editor_cmd = (
            shutil.which("code") or shutil.which("nvim") or shutil.which("vim") or "vi"
        )

        try:
            subprocess.Popen(
                [editor_cmd, abs_path],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.io.tool_output(
                f"Opened {os.path.basename(abs_path)} in {os.path.basename(editor_cmd)}"
            )
        except Exception as e:
            self.io.tool_error(f"Failed to open file: {e}")

    def completions_open(self):
        """Provide completions for /open command - files in chat."""
        files = self.coder.get_inchat_relative_files()
        read_only_files = [
            self.coder.get_rel_fname(fn) for fn in self.coder.abs_read_only_fnames
        ]
        all_files = files + read_only_files
        all_files = [self.quote_fname(fn) for fn in all_files]
        return all_files

    def cmd_think_tokens(self, args):
        """Set the thinking token budget, eg: 8096, 8k, 10.5k, 0.5M, or 0 to disable."""
        model = self.coder.main_model

        if not args.strip():
            # Display current value if no args are provided
            formatted_budget = model.get_thinking_tokens()
            if formatted_budget is None:
                self.io.tool_output("Thinking tokens are not currently set.")
            else:
                budget = model.get_raw_thinking_tokens()
                self.io.tool_output(
                    f"Current thinking token budget: {budget:,} tokens ({formatted_budget})."
                )
            return

        value = args.strip()
        model.set_thinking_tokens(value)

        # Handle the special case of 0 to disable thinking tokens
        if value == "0":
            self.io.tool_output("Thinking tokens disabled.")
        else:
            formatted_budget = model.get_thinking_tokens()
            budget = model.get_raw_thinking_tokens()
            self.io.tool_output(
                f"Set thinking token budget to {budget:,} tokens ({formatted_budget})."
            )

        self.io.tool_output()

        # Output announcements
        announcements = "\n".join(self.coder.get_announcements())
        self.io.tool_output(announcements)

    def cmd_reasoning_effort(self, args):
        "Set the reasoning effort level (values: number or low/medium/high depending on model)"
        model = self.coder.main_model

        if not args.strip():
            # Display current value if no args are provided
            reasoning_value = model.get_reasoning_effort()
            if reasoning_value is None:
                self.io.tool_output("Reasoning effort is not currently set.")
            else:
                self.io.tool_output(f"Current reasoning effort: {reasoning_value}")
            return

        value = args.strip()
        model.set_reasoning_effort(value)
        reasoning_value = model.get_reasoning_effort()
        self.io.tool_output(f"Set reasoning effort to {reasoning_value}")
        self.io.tool_output()

        # Output announcements
        announcements = "\n".join(self.coder.get_announcements())
        self.io.tool_output(announcements)

    def cmd_copy_context(self, args=None):
        """Copy the current chat context as markdown, suitable to paste into a web UI"""

        chunks = self.coder.format_chat_chunks()

        markdown = ""

        # Only include specified chunks in order
        for messages in [chunks.repo, chunks.readonly_files, chunks.chat_files]:
            for msg in messages:
                # Only include user messages
                if msg["role"] != "user":
                    continue

                content = msg["content"]

                # Handle image/multipart content
                if isinstance(content, list):
                    for part in content:
                        if part.get("type") == "text":
                            markdown += part["text"] + "\n\n"
                else:
                    markdown += content + "\n\n"

        args = args or ""
        markdown += f"""
Just tell me how to edit the files to make the changes.
Don't give me back entire files.
Just show me the edits I need to make.

{args}
"""

        try:
            pyperclip.copy(markdown)
            self.io.tool_output("Copied code context to clipboard.")
        except pyperclip.PyperclipException as e:
            self.io.tool_error(f"Failed to copy to clipboard: {str(e)}")
            self.io.tool_output(
                "You may need to install xclip or xsel on Linux, or pbcopy on macOS."
            )
        except Exception as e:
            self.io.tool_error(
                f"An unexpected error occurred while copying to clipboard: {str(e)}"
            )

    def cmd_preview(self, args):
        "Open the compiled PDF for preview"
        import subprocess
        import platform

        # Find the main tex file
        main_file = None
        for fname in self.coder.abs_fnames:
            if fname.endswith(".tex"):
                main_file = fname
                break

        if not main_file:
            self.io.tool_error("No .tex file found in the chat.")
            return

        # Construct PDF path
        pdf_path = main_file.rsplit(".", 1)[0] + ".pdf"

        if not os.path.exists(pdf_path):
            self.io.tool_error(f"PDF not found at {pdf_path}. Run /compile first.")
            return

        # Open PDF based on platform
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", pdf_path], check=True)
            elif platform.system() == "Windows":
                subprocess.run(["start", pdf_path], shell=True, check=True)
            else:  # Linux
                subprocess.run(["xdg-open", pdf_path], check=True)
            self.io.tool_output(f"Opened {pdf_path}")
        except Exception as e:
            self.io.tool_error(f"Failed to open PDF: {e}")

    def cmd_bib(self, args):
        "Manage bibliography references"
        if not args:
            self.io.tool_output("Usage: /bib <action> [args]")
            self.io.tool_output("Actions:")
            self.io.tool_output("  list     - List all .bib files in the chat")
            self.io.tool_output("  add <key> - Add a new reference entry")
            self.io.tool_output("  check    - Check for undefined references")
            return

        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else ""

        if action == "list":
            bib_files = [f for f in self.coder.abs_fnames if f.endswith(".bib")]
            if not bib_files:
                self.io.tool_output("No .bib files in the chat.")
            else:
                for bf in bib_files:
                    self.io.tool_output(f"  {bf}")
        elif action == "check":
            self.io.tool_output("Checking for undefined references...")
            # This would need LaTeX compilation output parsing
            self.io.tool_output("Run /compile to check for undefined references.")
        else:
            self.io.tool_output(f"Unknown bib action: {action}")

    def cmd_template(self, args):
        "Select or create a LaTeX template"
        templates = {
            "article": "\\documentclass{article}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath}\n\n\\title{Title}\n\\author{Author}\n\\date{\\today}\n\n\\begin{document}\n\\maketitle\n\n\\section{Introduction}\n\n\\end{document}",
            "report": "\\documentclass{report}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath}\n\n\\title{Title}\n\\author{Author}\n\\date{\\today}\n\n\\begin{document}\n\\maketitle\n\\tableofcontents\n\n\\chapter{Introduction}\n\n\\end{document}",
            "book": "\\documentclass{book}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath}\n\n\\title{Title}\n\\author{Author}\n\\date{\\today}\n\n\\begin{document}\n\\frontmatter\n\\maketitle\n\\tableofcontents\n\n\\mainmatter\n\\chapter{Introduction}\n\n\\backmatter\n\\end{document}",
            "beamer": "\\documentclass{beamer}\n\\usetheme{Madrid}\n\n\\title{Presentation Title}\n\\author{Author Name}\n\\institute{Institute}\n\\date{\\today}\n\n\\begin{document}\n\n\\begin{frame}\n\\titlepage\n\\end{frame}\n\n\\begin{frame}{Outline}\\tableofcontents\\end{frame}\n\n\\section{First Section}\n\\begin{frame}{Content}\\end{frame}\n\n\\end{document}",
        }

        if not args:
            self.io.tool_output("Available templates:")
            for name in templates:
                self.io.tool_output(f"  {name}")
            self.io.tool_output("Usage: /template <name> [filename.tex]")
            return

        parts = args.split()
        template_name = parts[0].lower()
        filename = parts[1] if len(parts) > 1 else "main.tex"

        if template_name not in templates:
            self.io.tool_error(f"Unknown template: {template_name}")
            return

        # Write template to file
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(templates[template_name])
            self.io.tool_output(f"Created {filename} with {template_name} template.")
        except Exception as e:
            self.io.tool_error(f"Error creating template: {e}")

    def _discover_templates(self):
        """Discover templates from template/ directory."""
        from pathlib import Path

        templates = {}

        # Try multiple locations for template directory
        possible_paths = [
            Path("template"),  # Relative to cwd
            Path(self.coder.root) / "template"
            if hasattr(self, "coder") and self.coder
            else None,
            Path(__file__).parent.parent / "template",  # Relative to commands.py
        ]

        template_dir = None
        for path in possible_paths:
            if path and path.exists():
                template_dir = path
                break

        if not template_dir:
            return templates

        for item in template_dir.iterdir():
            if item.is_dir():
                # Look for .tex files in subdirectory
                tex_files = list(item.glob("*.tex"))
                if tex_files:
                    # Use the first .tex file found
                    templates[item.name] = str(tex_files[0])

        return templates

    def cmd_init(self, args):
        """Initialize a new LaTeX project with template files.

        Usage: /init <project_name> [template_name]

        Creates a new folder with the project name and initializes it with:
        - Template style files (.cls, .sty, .bst, etc.)
        - A main .tex file with minimal compilable content
        - Fonts directory if available

        Does NOT delete or modify any existing files.
        """
        import shutil
        from pathlib import Path

        if not args:
            self.io.tool_output("Usage: /init <project_name> [template_name]")
            self.io.tool_output("")
            self.io.tool_output("Initialize a new LaTeX project with template files.")
            self.io.tool_output(
                "Creates a new folder with template style files and main .tex file."
            )
            self.io.tool_output("")
            self.io.tool_output("Examples:")
            self.io.tool_output(
                "  /init my_paper          # Create project with default template"
            )
            self.io.tool_output(
                "  /init my_paper wiley    # Create project with wiley template"
            )

            # Show available templates from template/ directory
            discovered = self._discover_templates()
            if discovered:
                self.io.tool_output("")
                self.io.tool_output("Available templates from template/ directory:")
                for name in sorted(discovered.keys()):
                    self.io.tool_output(f"  {name}")
            return

        parts = args.split()
        project_name = parts[0]
        template_name = parts[1] if len(parts) > 1 else None

        # Resolve project directory path
        if Path(project_name).is_absolute():
            project_dir = Path(project_name)
        else:
            if self.coder.use_cwd:
                project_dir = Path.cwd() / project_name
            else:
                project_dir = Path(self.coder.root) / project_name

        # Check if directory already exists
        if project_dir.exists():
            self.io.tool_error(f"Directory already exists: {project_dir}")
            self.io.tool_output(
                "Please choose a different name or remove the existing directory."
            )
            return

        # Discover templates
        discovered = self._discover_templates()

        # Determine template to use
        template_dir = None
        if template_name:
            if template_name in discovered:
                template_dir = Path(discovered[template_name]).parent
            else:
                self.io.tool_error(
                    f"Template '{template_name}' not found in template/ directory."
                )
                self.io.tool_output(
                    f"Available templates: {', '.join(sorted(discovered.keys()))}"
                )
                return
        else:
            # Use first available template if any
            if discovered:
                first_name = sorted(discovered.keys())[0]
                template_dir = Path(discovered[first_name]).parent
                self.io.tool_output(f"Using default template: {first_name}")

        # Create project directory
        try:
            project_dir.mkdir(parents=True, exist_ok=False)
            self.io.tool_output(f"Created project directory: {project_dir}")
        except Exception as e:
            self.io.tool_error(f"Error creating directory: {e}")
            return

        # Copy template files if template directory exists
        if template_dir and template_dir.exists():
            try:
                # Copy all files from template directory
                for item in template_dir.iterdir():
                    if item.is_dir():
                        # Copy subdirectories (like Fonts)
                        dest_dir = project_dir / item.name
                        shutil.copytree(item, dest_dir)
                        self.io.tool_output(f"Copied directory: {item.name}/")
                    else:
                        # Copy individual files
                        dest_file = project_dir / item.name
                        shutil.copy2(item, dest_file)
                        self.io.tool_output(f"Copied: {item.name}")

                # Copy .tex file as main.tex
                tex_files = list(template_dir.glob("*.tex"))
                if tex_files:
                    main_tex = project_dir / "main.tex"
                    # Read the template tex content
                    with open(tex_files[0], "r", encoding="utf-8") as f:
                        tex_content = f.read()
                    # Write as main.tex
                    with open(main_tex, "w", encoding="utf-8") as f:
                        f.write(tex_content)
                    self.io.tool_output("Created: main.tex")
            except Exception as e:
                self.io.tool_error(f"Error copying template files: {e}")
                return
        else:
            # No template, create minimal .tex file
            try:
                main_tex = project_dir / "main.tex"
                with open(main_tex, "w", encoding="utf-8") as f:
                    f.write(self._generate_minimal_template())
                self.io.tool_output("Created: main.tex (minimal template)")
            except Exception as e:
                self.io.tool_error(f"Error creating main.tex: {e}")
                return

        self.io.tool_output("")
        self.io.tool_output(f"Project initialized successfully: {project_dir}")
        self.io.tool_output("")
        self.io.tool_output("Next steps:")
        self.io.tool_output(f"  cd {project_name}")
        self.io.tool_output("  # Edit main.tex with your content")
        self.io.tool_output("  # Compile with: latexmk -pdf main.tex")

    def _generate_minimal_template(self):
        """Generate minimal LaTeX template with one example of each environment."""
        return r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}

\title{Title}
\author{Author}
\date{\today}

\begin{document}
\maketitle

\section{Section Title}

Text content here.

\subsection{Equation Example}

\begin{equation}
    E = mc^2
\label{eq:example}
\end{equation}

\subsection{Table Example}

\begin{table}[htbp]
    \centering
    \caption{Table caption}
    \label{tab:example}
    \begin{tabular}{ccc}
        \toprule
        Column 1 & Column 2 & Column 3 \\
        \midrule
        Data 1 & Data 2 & Data 3 \\
        Data 4 & Data 5 & Data 6 \\
        \bottomrule
    \end{tabular}
\end{table}

\subsection{Figure Example}

\begin{figure}[htbp]
    \centering
    % Replace placeholder.png with your image file
    \includegraphics[width=0.5\textwidth]{placeholder.png}
    \caption{Figure caption}
    \label{fig:example}
\end{figure}

\end{document}
"""

    def _extract_and_minimize_template(self, template_content):
        """Extract preamble from template and combine with minimal content."""
        import re

        # Extract everything before \begin{document}
        preamble_match = re.search(
            r"(.*?\\begin\{document\})", template_content, re.DOTALL
        )
        if not preamble_match:
            # If no \begin{document} found, use default template
            return self._generate_minimal_template()

        preamble = preamble_match.group(1)

        # Check if there's content after \begin{document} that we should preserve
        # Look for \title, \author, \maketitle
        title_match = re.search(r"(\\title(?:\[[^\]]*\])?\{[^}]+\})", template_content)
        author_match = re.search(
            r"(\\author(?:\[[^\]]*\])?\{[^}]+\})", template_content
        )

        # Build minimal content
        minimal_content = preamble + "\n"

        # Add title and author if found
        if title_match:
            minimal_content += "\n" + title_match.group(1)
        else:
            minimal_content += "\n\\title{Title}"

        if author_match:
            minimal_content += "\n" + author_match.group(1)
        else:
            minimal_content += "\n\\author{Author}"

        minimal_content += "\n\\date{\\today}"
        minimal_content += "\n"
        minimal_content += "\n\\maketitle"
        minimal_content += "\n"
        minimal_content += "\n\\section{Section Title}"
        minimal_content += "\n"
        minimal_content += "\nText content here."
        minimal_content += "\n"
        minimal_content += "\n\\subsection{Equation Example}"
        minimal_content += "\n"
        minimal_content += "\n\\begin{equation}"
        minimal_content += "\n    E = mc^2"
        minimal_content += "\n\\label{eq:example}"
        minimal_content += "\n\\end{equation}"
        minimal_content += "\n"
        minimal_content += "\n\\subsection{Table Example}"
        minimal_content += "\n"
        minimal_content += "\n\\begin{table}[htbp]"
        minimal_content += "\n    \\centering"
        minimal_content += "\n    \\caption{Table caption}"
        minimal_content += "\n    \\label{tab:example}"
        minimal_content += "\n    \\begin{tabular}{ccc}"
        minimal_content += "\n        \\toprule"
        minimal_content += "\n        Column 1 & Column 2 & Column 3 \\\\"
        minimal_content += "\n        \\midrule"
        minimal_content += "\n        Data 1 & Data 2 & Data 3 \\\\"
        minimal_content += "\n        Data 4 & Data 5 & Data 6 \\\\"
        minimal_content += "\n        \\bottomrule"
        minimal_content += "\n    \\end{tabular}"
        minimal_content += "\n\\end{table}"
        minimal_content += "\n"
        minimal_content += "\n\\subsection{Figure Example}"
        minimal_content += "\n"
        minimal_content += "\n\\begin{figure}[htbp]"
        minimal_content += "\n    \\centering"
        minimal_content += "\n    % Replace placeholder.png with your image file"
        minimal_content += (
            "\n    \\includegraphics[width=0.5\\textwidth]{placeholder.png}"
        )
        minimal_content += "\n    \\caption{Figure caption}"
        minimal_content += "\n    \\label{fig:example}"
        minimal_content += "\n\\end{figure}"
        minimal_content += "\n"
        minimal_content += "\n\\end{document}"
        minimal_content += "\n"

        return minimal_content

    def cmd_wordcount(self, args):
        "Count words in LaTeX files"
        import re

        tex_files = [f for f in self.coder.abs_fnames if f.endswith(".tex")]
        if not tex_files:
            self.io.tool_error("No .tex files in the chat.")
            return

        total_words = 0
        for fname in tex_files:
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    content = f.read()
                # Remove LaTeX commands and comments
                content = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})*", "", content)
                content = re.sub(r"%.*", "", content)
                content = re.sub(r"\\[a-zA-Z]+", "", content)
                # Count words
                words = len(content.split())
                total_words += words
                self.io.tool_output(f"{fname}: {words} words")
            except Exception as e:
                self.io.tool_error(f"Error reading {fname}: {e}")

        if len(tex_files) > 1:
            self.io.tool_output(f"\nTotal: {total_words} words")

    def cmd_add_template(self, args):
        """Parse a LaTeX template and generate a prompt template for content filling."""
        import re

        if not args:
            self.io.tool_output("Usage: /add-template <filename.tex> [output.md]")
            self.io.tool_output("")
            self.io.tool_output(
                "Parse a LaTeX template and generate a prompt template."
            )
            self.io.tool_output(
                "The prompt template can be used to guide LLM to fill in content."
            )
            return

        parts = args.split()
        filename = parts[0]
        output_file = parts[1] if len(parts) > 1 else None

        abs_path = self.coder.abs_root_path(filename)

        if not os.path.exists(abs_path):
            self.io.tool_error(f"File not found: {filename}")
            return

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            # ── 提取文档类和包 ──────────────────────────────
            doc_class_match = re.search(
                r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", content
            )
            doc_class = doc_class_match.group(1) if doc_class_match else "article"

            packages = re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", content)

            # ── 提取文档结构 ────────────────────────────────
            sections = []
            for match in re.finditer(
                r"\\(section|subsection|subsubsection)\{([^}]+)\}", content
            ):
                level = match.group(1)
                title = match.group(2)
                sections.append((level, title))

            # ── 提取特殊环境 ────────────────────────────────
            env_pattern = r"\\begin\{(figure|table|equation|align|gather|algorithm|listing|lstlisting)\}.*?\\end\{\1\}"
            environments = re.findall(env_pattern, content, re.DOTALL)
            env_counts = {}
            for env in environments:
                env_counts[env] = env_counts.get(env, 0) + 1

            # ── 提取已有内容的环境 ──────────────────────────
            filled_envs = {}
            for env_name in ["figure", "table", "equation", "align", "algorithm"]:
                pattern = r"\\begin\{" + env_name + r"\}.*?\\end\{" + env_name + r"\}"
                matches = re.findall(pattern, content, re.DOTALL)
                for m in matches:
                    # 检查是否有实际内容（不仅仅是框架）
                    inner = re.sub(
                        r"\\begin\{[^}]+\}|\\end\{[^}]+\}|\\label\{[^}]+\}|\\caption\{[^}]+\}",
                        "",
                        m,
                    )
                    if inner.strip() and len(inner.strip()) > 20:
                        filled_envs[env_name] = filled_envs.get(env_name, 0) + 1

            # ── 提取引用和标签 ──────────────────────────────
            labels = re.findall(r"\\label\{([^}]+)\}", content)
            refs = re.findall(r"\\(?:ref|eqref|autoref|cref)\{([^}]+)\}", content)
            cites = re.findall(r"\\cite\{([^}]+)\}", content)

            # ── 生成提示词模板 ──────────────────────────────
            prompt_lines = []
            prompt_lines.append("# LaTeX Document Template Analysis")
            prompt_lines.append("")
            prompt_lines.append("## Document Info")
            prompt_lines.append(f"- Document class: `{doc_class}`")
            if packages:
                prompt_lines.append(
                    f"- Packages: {', '.join(f'`{p}`' for p in packages)}"
                )
            prompt_lines.append("")

            if sections:
                prompt_lines.append("## Document Structure")
                prompt_lines.append("")
                for level, title in sections:
                    indent = "  " * (
                        ["section", "subsection", "subsubsection"].index(level)
                    )
                    prompt_lines.append(f"{indent}- {title}")
                prompt_lines.append("")

            # 分析需要填充的部分
            empty_sections = []
            for level, title in sections:
                # 简单检查：如果章节标题后没有实质内容
                section_pattern = re.escape(f"\\{level}{{{title}}}")
                section_match = re.search(section_pattern, content)
                if section_match:
                    after_section = content[section_match.end() :]
                    # 找到下一个同级或更高级别的章节
                    next_section = re.search(
                        r"\\(section|subsection|subsubsection)\{", after_section
                    )
                    if next_section:
                        section_content = after_section[: next_section.start()]
                    else:
                        section_content = after_section[:500]  # 只检查前500字符
                    # 如果内容太少，认为是空的
                    if len(section_content.strip()) < 50:
                        empty_sections.append(title)

            if empty_sections:
                prompt_lines.append("## Sections Need Content")
                prompt_lines.append("")
                for s in empty_sections:
                    prompt_lines.append(f"- **{s}**: [需要填充内容]")
                prompt_lines.append("")

            if env_counts:
                prompt_lines.append("## Special Environments")
                prompt_lines.append("")
                for env, count in env_counts.items():
                    filled = filled_envs.get(env, 0)
                    prompt_lines.append(
                        f"- `{env}`: {count} total, {filled} filled, {count - filled} empty"
                    )
                prompt_lines.append("")

            if cites:
                prompt_lines.append("## Citations")
                prompt_lines.append("")
                prompt_lines.append(f"- Total citations: {len(cites)}")
                prompt_lines.append(
                    f"- Keys: {', '.join(cites[:10])}{'...' if len(cites) > 10 else ''}"
                )
                prompt_lines.append("")

            # ── 生成写作任务提示 ──────────────────────────
            prompt_lines.append("## Writing Tasks")
            prompt_lines.append("")
            prompt_lines.append(
                "Based on the template analysis, here are the tasks to complete:"
            )
            prompt_lines.append("")

            task_num = 1
            for s in empty_sections:
                prompt_lines.append(f"{task_num}. Write content for section **{s}**")
                task_num += 1

            for env, count in env_counts.items():
                filled = filled_envs.get(env, 0)
                empty = count - filled
                if empty > 0:
                    prompt_lines.append(
                        f"{task_num}. Create {empty} {env} environment(s)"
                    )
                    task_num += 1

            prompt_template = "\n".join(prompt_lines)

            # ── 输出结果 ────────────────────────────────────
            self.io.tool_output("=" * 60)
            self.io.tool_output(prompt_template)
            self.io.tool_output("=" * 60)

            # ── 保存到文件（如果指定）──────────────────────
            if output_file:
                output_path = self.coder.abs_root_path(output_file)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(prompt_template)
                self.io.tool_output(f"\n✅ Prompt template saved to: {output_file}")
            else:
                self.io.tool_output(
                    f"\nTip: /add-template {filename} output.md  # Save to file"
                )

        except Exception as e:
            self.io.tool_error(f"Error parsing template: {e}")


def expand_subdir(file_path):
    if file_path.is_file():
        yield file_path
        return

    if file_path.is_dir():
        for file in file_path.rglob("*"):
            if file.is_file():
                yield file


def parse_quoted_filenames(args):
    filenames = re.findall(r"\"(.+?)\"|(\S+)", args)
    filenames = [name for sublist in filenames for name in sublist if name]
    return filenames


def get_help_md():
    md = Commands(None, None).get_help_md()
    return md


def main():
    md = get_help_md()
    print(md)


if __name__ == "__main__":
    status = main()
    sys.exit(status)
