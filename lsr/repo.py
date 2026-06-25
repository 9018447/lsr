import contextlib
import os
import subprocess
import time
from pathlib import Path, PurePosixPath

try:
    import git

    GITPYTHON_AVAILABLE = True
    GIT_ERRORS = [
        git.exc.ODBError,
        git.exc.GitError,
        git.exc.InvalidGitRepositoryError,
        git.exc.GitCommandNotFound,
    ]
except ImportError:
    git = None
    GITPYTHON_AVAILABLE = False
    GIT_ERRORS = []

import pathspec

from lsr import prompts, utils

from .dump import dump  # noqa: F401
from .waiting import WaitingSpinner

ANY_VCS_ERROR = tuple(
    GIT_ERRORS
    + [
        OSError,
        IndexError,
        BufferError,
        TypeError,
        ValueError,
        AttributeError,
        AssertionError,
        TimeoutError,
        subprocess.SubprocessError,
        FileNotFoundError,
    ]
)

# Keep the old export name for backward compatibility.
ANY_GIT_ERROR = ANY_VCS_ERROR


def _run_cmd(cmd, cwd=None, capture_output=True, text=True, check=False, env=None):
    """Thin wrapper around subprocess.run with sensible defaults."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        check=check,
        env=env,
        encoding="utf-8",
        errors="replace",
    )


@contextlib.contextmanager
def set_env(var_name, value, original_value):
    """Temporarily set an environment variable."""
    os.environ[var_name] = value
    try:
        yield
    finally:
        if original_value is not None:
            os.environ[var_name] = original_value
        elif var_name in os.environ:
            del os.environ[var_name]


def find_repo_root(fnames, git_dname):
    """Find the unique repository root and determine whether it is a jj or git repo.

    Returns a tuple (vcs, root) where vcs is 'jj' or 'git'.
    Raises FileNotFoundError if no repo is found.
    """
    if git_dname:
        check_fnames = [git_dname]
    elif fnames:
        check_fnames = fnames
    else:
        check_fnames = ["."]

    repo_infos = []
    for fname in check_fnames:
        fname = Path(fname)
        fname = fname.resolve()

        if not fname.exists() and fname.parent.exists():
            fname = fname.parent

        # Prefer jj if a .jj directory exists anywhere in the ancestry.
        try:
            jj_root = _run_cmd(["jj", "root"], cwd=str(fname), check=True).stdout.strip()
            if jj_root:
                repo_infos.append(("jj", utils.safe_abs_path(jj_root)))
                continue
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

        if git is not None:
            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_infos.append(("git", utils.safe_abs_path(repo_path)))
            except tuple(GIT_ERRORS):
                pass

    if not repo_infos:
        raise FileNotFoundError

    root_set = set(info[1] for info in repo_infos)

    if len(root_set) > 1:
        raise FileNotFoundError

    return repo_infos[0]


class BaseRepo:
    """Shared behavior for VCS backends (path/ignore normalization)."""

    repo = None
    lsr_ignore_file = None
    lsr_ignore_spec = None
    lsr_ignore_ts = 0
    lsr_ignore_last_check = 0
    subtree_only = False
    ignore_file_cache = {}
    vcs_error = None
    vcs = "unknown"

    def __init__(
        self,
        io,
        root,
        lsr_ignore_file=None,
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
        subtree_only=False,
        commit_verify=True,
        attribute_co_authored_by=False,
        use_cwd=True,
    ):
        self.io = io
        self.models = models
        self.root = utils.safe_abs_path(root)

        self.normalized_path = {}
        self.tree_files = {}
        self.use_cwd = use_cwd
        self.ignore_file_cache = {}

        self.attribute_author = attribute_author
        self.attribute_committer = attribute_committer
        self.attribute_commit_message_author = attribute_commit_message_author
        self.attribute_commit_message_committer = attribute_commit_message_committer
        self.attribute_co_authored_by = attribute_co_authored_by
        self.commit_prompt = commit_prompt
        self.subtree_only = subtree_only
        self.commit_verify = commit_verify

        if lsr_ignore_file:
            self.lsr_ignore_file = Path(lsr_ignore_file)

    # ------------------------------------------------------------------
    # Abstract / backend-specific hooks
    # ------------------------------------------------------------------
    def is_dirty(self, path=None):
        raise NotImplementedError

    def get_tracked_files(self):
        raise NotImplementedError

    def get_dirty_files(self):
        raise NotImplementedError

    def commit(
        self, fnames=None, context=None, message=None, lsr_edits=False, coder=None
    ):
        raise NotImplementedError

    def get_head_commit(self):
        raise NotImplementedError

    def get_head_commit_sha(self, short=False):
        raise NotImplementedError

    def get_head_commit_message(self, default=None):
        raise NotImplementedError

    def diff_commits(self, pretty, from_commit, to_commit):
        raise NotImplementedError

    def git_ignored_file(self, path):
        raise NotImplementedError

    def add_file(self, path):
        raise NotImplementedError

    def get_rel_repo_dir(self):
        raise NotImplementedError

    def current_bookmark(self):
        raise NotImplementedError

    def undo_last_commit(self, commit_hash):
        """Undo the commit identified by `commit_hash`.

        Raises ValueError with a user-facing message when the operation cannot
        proceed safely.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def normalize_path(self, path):
        orig_path = path
        res = self.normalized_path.get(orig_path)
        if res:
            return res

        if self.use_cwd:
            cwd = Path.cwd()
            try:
                path_obj = Path(path)
                if path_obj.is_absolute():
                    path = str(path_obj.relative_to(cwd))
                else:
                    abs_path = Path(self.root) / path
                    path = str(abs_path.relative_to(cwd))
            except ValueError:
                path = str(path)
        else:
            path = str(
                Path(PurePosixPath((Path(self.root) / path).relative_to(self.root)))
            )

        self.normalized_path[orig_path] = path
        return path

    def refresh_lsr_ignore(self):
        if not self.lsr_ignore_file:
            return

        current_time = time.time()
        if current_time - self.lsr_ignore_last_check < 1:
            return

        self.lsr_ignore_last_check = current_time

        if not self.lsr_ignore_file.is_file():
            return

        mtime = self.lsr_ignore_file.stat().st_mtime
        if mtime != self.lsr_ignore_ts:
            self.lsr_ignore_ts = mtime
            self.ignore_file_cache = {}
            lines = self.lsr_ignore_file.read_text().splitlines()
            self.lsr_ignore_spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                lines,
            )

    def ignored_file(self, fname):
        self.refresh_lsr_ignore()

        if fname in self.ignore_file_cache:
            return self.ignore_file_cache[fname]

        result = self.ignored_file_raw(fname)
        self.ignore_file_cache[fname] = result
        return result

    def ignored_file_raw(self, fname):
        if self.subtree_only:
            try:
                fname_path = Path(self.normalize_path(fname))
                cwd_path = Path.cwd().resolve().relative_to(Path(self.root).resolve())
            except ValueError:
                return True

            if cwd_path not in fname_path.parents and fname_path != cwd_path:
                return True

        if not self.lsr_ignore_file or not self.lsr_ignore_file.is_file():
            return False

        try:
            fname = self.normalize_path(fname)
        except ValueError:
            return True

        return self.lsr_ignore_spec.match_file(fname)

    def path_in_repo(self, path):
        if not path:
            return

        tracked_files = set(self.get_tracked_files())
        normalized = self.normalize_path(path)
        return normalized in tracked_files

    def abs_root_path(self, path):
        if self.use_cwd:
            res = Path.cwd() / path
        else:
            res = Path(self.root) / path
        return utils.safe_abs_path(res)

    def get_commit_message(self, diffs, context, user_language=None):
        diffs = "# Diffs:\n" + diffs

        content = ""
        if context:
            content += context + "\n"
        content += diffs

        system_content = self.commit_prompt or prompts.commit_system

        language_instruction = ""
        if user_language:
            language_instruction = f"\n- Is written in {user_language}."
        system_content = system_content.format(
            language_instruction=language_instruction
        )

        commit_message = None
        for model in self.models:
            spinner_text = f"Generating commit message with {model.name}"
            with WaitingSpinner(spinner_text):
                if model.system_prompt_prefix:
                    current_system_content = (
                        model.system_prompt_prefix + "\n" + system_content
                    )
                else:
                    current_system_content = system_content

                messages = [
                    dict(role="system", content=current_system_content),
                    dict(role="user", content=content),
                ]

                num_tokens = model.token_count(messages)
                max_tokens = model.info.get("max_input_tokens") or 0

                if max_tokens and num_tokens > max_tokens:
                    continue

                commit_message = model.simple_send_with_retries(messages)
                if commit_message:
                    break

        if not commit_message:
            self.io.tool_error("Failed to generate commit message!")
            return

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message


class GitRepo(BaseRepo):
    """Git backend implemented with GitPython."""

    vcs = "git"

    def __init__(self, io, root, **kwargs):
        super().__init__(io, root, **kwargs)
        self.repo = git.Repo(self.root, odbt=git.GitDB)

    def commit(
        self, fnames=None, context=None, message=None, lsr_edits=False, coder=None
    ):
        if not fnames and not self.repo.is_dirty():
            return

        diffs = self.get_diffs(fnames)
        if not diffs:
            return

        if message:
            commit_message = message
        else:
            user_language = None
            if coder:
                user_language = coder.commit_language
                if not user_language:
                    user_language = coder.get_user_language()
            commit_message = self.get_commit_message(diffs, context, user_language)

        if coder and hasattr(coder, "args"):
            attribute_author = coder.args.attribute_author
            attribute_committer = coder.args.attribute_committer
            attribute_commit_message_author = coder.args.attribute_commit_message_author
            attribute_commit_message_committer = (
                coder.args.attribute_commit_message_committer
            )
            attribute_co_authored_by = coder.args.attribute_co_authored_by
        else:
            attribute_author = self.attribute_author
            attribute_committer = self.attribute_committer
            attribute_commit_message_author = self.attribute_commit_message_author
            attribute_commit_message_committer = self.attribute_commit_message_committer
            attribute_co_authored_by = self.attribute_co_authored_by

        author_explicit = attribute_author is not None
        committer_explicit = attribute_committer is not None

        effective_author = True if attribute_author is None else attribute_author
        effective_committer = True if attribute_committer is None else attribute_committer

        prefix_commit_message = lsr_edits and (
            attribute_commit_message_author or attribute_commit_message_committer
        )

        commit_message_trailer = ""
        if lsr_edits and attribute_co_authored_by:
            model_name = "unknown-model"
            if coder and hasattr(coder, "main_model") and coder.main_model.name:
                model_name = coder.main_model.name
            commit_message_trailer = (
                f"\n\nCo-authored-by: lsr ({model_name}) <lsr@your-username.github.io/lsr>"
            )

        use_attribute_author = (
            lsr_edits
            and effective_author
            and (not attribute_co_authored_by or author_explicit)
        )

        use_attribute_committer = effective_committer and (
            not (lsr_edits and attribute_co_authored_by) or committer_explicit
        )

        if not commit_message:
            commit_message = "(no commit message provided)"

        if prefix_commit_message:
            commit_message = "lsr: " + commit_message

        full_commit_message = commit_message + commit_message_trailer

        cmd = ["-m", full_commit_message]
        if not self.commit_verify:
            cmd.append("--no-verify")
        if fnames:
            fnames = [str(self.abs_root_path(fn)) for fn in fnames]
            for fname in fnames:
                try:
                    self.repo.git.add(fname)
                except ANY_VCS_ERROR as err:
                    self.io.tool_error(f"Unable to add {fname}: {err}")
            cmd += ["--"] + fnames
        else:
            cmd += ["-a"]

        original_user_name = self.repo.git.config("--get", "user.name")
        original_committer_name_env = os.environ.get("GIT_COMMITTER_NAME")
        original_author_name_env = os.environ.get("GIT_AUTHOR_NAME")
        committer_name = f"{original_user_name} (lsr)"

        try:
            with contextlib.ExitStack() as stack:
                if use_attribute_committer:
                    stack.enter_context(
                        set_env(
                            "GIT_COMMITTER_NAME",
                            committer_name,
                            original_committer_name_env,
                        )
                    )
                if use_attribute_author:
                    stack.enter_context(
                        set_env(
                            "GIT_AUTHOR_NAME", committer_name, original_author_name_env
                        )
                    )

                self.repo.git.commit(cmd)
                commit_hash = self.get_head_commit_sha(short=True)
                self.io.tool_output(f"Commit {commit_hash} {commit_message}", bold=True)
                return commit_hash, commit_message

        except ANY_VCS_ERROR as err:
            self.io.tool_error(f"Unable to commit: {err}")

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except (ValueError, OSError):
            return self.repo.git_dir

    def get_diffs(self, fnames=None):
        current_branch_has_commits = False
        try:
            active_branch = self.repo.active_branch
            try:
                commits = self.repo.iter_commits(active_branch)
                current_branch_has_commits = any(commits)
            except ANY_VCS_ERROR:
                pass
        except (TypeError,) + ANY_VCS_ERROR:
            pass

        if not fnames:
            fnames = []

        diffs = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        try:
            if current_branch_has_commits:
                args = ["HEAD", "--"] + list(fnames)
                diffs += self.repo.git.diff(*args, stdout_as_string=False).decode(
                    self.io.encoding, "replace"
                )
                return diffs

            wd_args = ["--"] + list(fnames)
            index_args = ["--cached"] + wd_args

            diffs += self.repo.git.diff(*index_args, stdout_as_string=False).decode(
                self.io.encoding, "replace"
            )
            diffs += self.repo.git.diff(*wd_args, stdout_as_string=False).decode(
                self.io.encoding, "replace"
            )

            return diffs
        except ANY_VCS_ERROR as err:
            self.io.tool_error(f"Unable to diff: {err}")

    def diff_commits(self, pretty, from_commit, to_commit):
        args = []
        if pretty:
            args += ["--color"]
        else:
            args += ["--color=never"]

        args += [from_commit, to_commit]
        diffs = self.repo.git.diff(*args, stdout_as_string=False).decode(
            self.io.encoding, "replace"
        )

        return diffs

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None
        except ANY_VCS_ERROR as err:
            self.vcs_error = err
            self.io.tool_error(f"Unable to list files in git repo: {err}")
            self.io.tool_output("Is your git repo corrupted?")
            return []

        files = set()
        if commit:
            if commit in self.tree_files:
                files = self.tree_files[commit]
            else:
                try:
                    iterator = commit.tree.traverse()
                    blob = None
                    while True:
                        try:
                            blob = next(iterator)
                            if blob.type == "blob":
                                files.add(blob.path)
                        except IndexError:
                            self.io.tool_warning(
                                "GitRepo: Index error encountered while reading git tree object."
                                " Skipping."
                            )
                            continue
                        except StopIteration:
                            break
                except ANY_VCS_ERROR as err:
                    self.vcs_error = err
                    self.io.tool_error(f"Unable to list files in git repo: {err}")
                    self.io.tool_output("Is your git repo corrupted?")
                    return []
                files = set(self.normalize_path(path) for path in files)
                self.tree_files[commit] = set(files)

        index = self.repo.index
        try:
            staged_files = [path for path, _ in index.entries.keys()]
            files.update(self.normalize_path(path) for path in staged_files)
        except ANY_VCS_ERROR as err:
            self.io.tool_error(f"Unable to read staged files: {err}")

        res = [fname for fname in files if not self.ignored_file(fname)]

        return res

    def git_ignored_file(self, path):
        if not self.repo:
            return
        try:
            if self.repo.ignored(path):
                return True
        except ANY_VCS_ERROR:
            return False

    def get_dirty_files(self):
        dirty_files = set()

        staged_files = self.repo.git.diff("--name-only", "--cached").splitlines()
        dirty_files.update(staged_files)

        unstaged_files = self.repo.git.diff("--name-only").splitlines()
        dirty_files.update(unstaged_files)

        return list(dirty_files)

    def is_dirty(self, path=None):
        if path and not self.path_in_repo(path):
            return True

        return self.repo.is_dirty(path=path)

    def get_head_commit(self):
        try:
            return self.repo.head.commit
        except (ValueError,) + ANY_VCS_ERROR:
            return None

    def get_head_commit_sha(self, short=False):
        commit = self.get_head_commit()
        if not commit:
            return
        if short:
            return commit.hexsha[:7]
        return commit.hexsha

    def get_head_commit_message(self, default=None):
        commit = self.get_head_commit()
        if not commit:
            return default
        return commit.message

    def add_file(self, path):
        self.repo.git.add(str(self.abs_root_path(path)))

    def current_bookmark(self):
        try:
            return str(self.repo.active_branch)
        except ANY_VCS_ERROR:
            return None

    def undo_last_commit(self, commit_hash):
        last_commit = self.get_head_commit()
        if not last_commit or not last_commit.parents:
            raise ValueError("This is the first commit in the repository. Cannot undo.")

        last_commit_hash = self.get_head_commit_sha(short=True)
        if last_commit_hash != commit_hash:
            raise ValueError(
                "The last commit was not made by lsr in this chat session."
            )

        if len(last_commit.parents) > 1:
            raise ValueError(
                f"The last commit {last_commit.hexsha} has more than 1 parent, can't undo."
            )

        prev_commit = last_commit.parents[0]
        changed_files_last_commit = [item.a_path for item in last_commit.diff(prev_commit)]

        for fname in changed_files_last_commit:
            if self.repo.is_dirty(path=fname):
                raise ValueError(
                    f"The file {fname} has uncommitted changes. Please stash them before undoing."
                )

            try:
                prev_commit.tree[fname]
            except KeyError:
                raise ValueError(
                    f"The file {fname} was not in the repository in the previous commit. Cannot"
                    " undo safely."
                )

        local_head = self.repo.git.rev_parse("HEAD")
        current_branch = self.repo.active_branch.name
        try:
            remote_head = self.repo.git.rev_parse(f"origin/{current_branch}")
            has_origin = True
        except ANY_VCS_ERROR:
            has_origin = False

        if has_origin:
            if local_head == remote_head:
                raise ValueError(
                    "The last commit has already been pushed to the origin. Undoing is not"
                    " possible."
                )

        unrestored = set()
        for file_path in changed_files_last_commit:
            try:
                self.repo.git.checkout("HEAD~1", file_path)
            except ANY_VCS_ERROR:
                unrestored.add(file_path)

        if unrestored:
            raise ValueError(
                "Error restoring files, aborting undo."
                f"\nUnable to restore files: {', '.join(sorted(unrestored))}"
            )

        self.repo.git.reset("--soft", "HEAD~1")


class JjRepo(BaseRepo):
    """Jujutsu backend for colocated jj+git repositories.

    We treat the working copy parent (@-) as the equivalent of git HEAD and the
    working copy (@) as the unstaged working tree.  The commit() workflow is:
        1. describe @ with the message
        2. jj new  (finalise @ as @-, create a new empty working copy)
        3. for files not in fnames, restore them from @-- into @ so that @-
           contains only the requested files.
    """

    vcs = "jj"

    def _jj(self, *args, check=True, env=None):
        cmd = ["jj", "--no-pager"] + list(args)
        res = _run_cmd(cmd, cwd=self.root, check=check, env=env)
        return res

    def _jj_text(self, *args, check=True, env=None):
        return self._jj(*args, check=check, env=env).stdout

    def _rev_exists(self, rev):
        try:
            self._jj("log", "-r", rev, "--no-graph", "-T", "", check=True)
            return True
        except ANY_VCS_ERROR:
            return False

    def _resolve_commit_id(self, rev, short=False):
        template = "commit_id.short(7)" if short else "commit_id"
        return self._jj_text("log", "-r", rev, "--no-graph", "-T", template).strip() or None

    def _resolve_change_id(self, rev):
        return self._jj_text("log", "-r", rev, "--no-graph", "-T", "change_id").strip() or None

    def _rev_message(self, rev):
        return self._jj_text("log", "-r", rev, "--no-graph", "-T", "description").strip() or None

    def is_dirty(self, path=None):
        if path and not self.path_in_repo(path):
            return True

        cmd = ["diff", "--summary"]
        if path:
            cmd.extend(["--", str(path)])
        try:
            text = self._jj_text(*cmd)
            return bool(text.strip())
        except ANY_VCS_ERROR:
            return True

    def get_tracked_files(self):
        try:
            text = self._jj_text("file", "list", "-r", "@")
        except ANY_VCS_ERROR as err:
            self.vcs_error = err
            self.io.tool_error(f"Unable to list files in jj repo: {err}")
            return []

        files = set()
        for line in text.splitlines():
            line = line.strip()
            if line:
                files.add(line)

        files = set(self.normalize_path(path) for path in files)
        res = [fname for fname in files if not self.ignored_file(fname)]
        return res

    def get_dirty_files(self):
        try:
            text = self._jj_text("diff", "--summary")
        except ANY_VCS_ERROR as err:
            self.io.tool_error(f"Unable to list dirty files: {err}")
            return []

        dirty_files = set()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # jj diff --summary lines look like: "M path/to/file" or "A path/to/file"
            parts = line.split(None, 1)
            if len(parts) == 2:
                dirty_files.add(parts[1])
        return list(dirty_files)

    def git_ignored_file(self, path):
        try:
            res = _run_cmd(
                ["git", "check-ignore", "-q", str(path)], cwd=self.root, check=False
            )
            return res.returncode == 0
        except ANY_VCS_ERROR:
            return False

    def add_file(self, path):
        # jj auto-tracks new files on snapshot; no explicit add needed.
        pass

    def get_rel_repo_dir(self):
        jj_dir = Path(self.root) / ".jj"
        try:
            return os.path.relpath(str(jj_dir), os.getcwd())
        except (ValueError, OSError):
            return str(jj_dir)

    def get_diffs(self, fnames=None):
        if not self._rev_exists("@-"):
            # No parent yet; compare working copy to empty tree.
            from_rev = "root()"
        else:
            from_rev = "@-"

        if not fnames:
            fnames = []

        diffs = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        cmd = ["diff", "--git", "--from", from_rev, "--to", "@"] + list(fnames)
        try:
            diffs += self._jj_text(*cmd)
        except ANY_VCS_ERROR as err:
            self.io.tool_error(f"Unable to diff: {err}")

        return diffs

    def diff_commits(self, pretty, from_commit, to_commit):
        args = ["diff", "--git", "--from", from_commit, "--to", to_commit]
        if pretty:
            args.append("--color=always")
        else:
            args.append("--color=never")
        return self._jj_text(*args)

    def commit(
        self, fnames=None, context=None, message=None, lsr_edits=False, coder=None
    ):
        if not self.is_dirty():
            return

        diffs = self.get_diffs(fnames)
        if not diffs:
            return

        if message:
            commit_message = message
        else:
            user_language = None
            if coder:
                user_language = coder.commit_language
                if not user_language:
                    user_language = coder.get_user_language()
            commit_message = self.get_commit_message(diffs, context, user_language)

        if coder and hasattr(coder, "args"):
            attribute_author = coder.args.attribute_author
            attribute_committer = coder.args.attribute_committer
            attribute_commit_message_author = coder.args.attribute_commit_message_author
            attribute_commit_message_committer = (
                coder.args.attribute_commit_message_committer
            )
            attribute_co_authored_by = coder.args.attribute_co_authored_by
        else:
            attribute_author = self.attribute_author
            attribute_committer = self.attribute_committer
            attribute_commit_message_author = self.attribute_commit_message_author
            attribute_commit_message_committer = self.attribute_commit_message_committer
            attribute_co_authored_by = self.attribute_co_authored_by

        author_explicit = attribute_author is not None
        committer_explicit = attribute_committer is not None

        effective_author = True if attribute_author is None else attribute_author
        effective_committer = True if attribute_committer is None else attribute_committer

        prefix_commit_message = lsr_edits and (
            attribute_commit_message_author or attribute_commit_message_committer
        )

        commit_message_trailer = ""
        if lsr_edits and attribute_co_authored_by:
            model_name = "unknown-model"
            if coder and hasattr(coder, "main_model") and coder.main_model.name:
                model_name = coder.main_model.name
            commit_message_trailer = (
                f"\n\nCo-authored-by: lsr ({model_name}) <lsr@your-username.github.io/lsr>"
            )

        use_attribute_author = (
            lsr_edits
            and effective_author
            and (not attribute_co_authored_by or author_explicit)
        )

        use_attribute_committer = effective_committer and (
            not (lsr_edits and attribute_co_authored_by) or committer_explicit
        )

        if not commit_message:
            commit_message = "(no commit message provided)"

        if prefix_commit_message:
            commit_message = "lsr: " + commit_message

        full_commit_message = commit_message + commit_message_trailer

        original_user_name = None
        try:
            original_user_name = _run_cmd(
                ["git", "config", "--get", "user.name"], cwd=self.root, check=True
            ).stdout.strip()
        except ANY_VCS_ERROR:
            pass

        committer_name = f"{original_user_name} (lsr)" if original_user_name else "lsr"

        env = dict(os.environ)
        if use_attribute_committer:
            env["GIT_COMMITTER_NAME"] = committer_name
        if use_attribute_author:
            env["GIT_AUTHOR_NAME"] = committer_name

        try:
            self._jj("describe", "-m", full_commit_message, env=env)

            if fnames:
                selected = [str(self.normalize_path(f)) for f in fnames]
                # Split the working copy so selected files stay in the commit
                # and remaining changes move to the new working copy.
                split_env = dict(env)
                split_env.setdefault("JJ_EDITOR", "true")
                split_env.setdefault("EDITOR", "true")
                self._jj("split", "-r", "@", "--", *selected, env=split_env)
            else:
                self._jj("new", env=env)

            commit_hash = self.get_head_commit_sha(short=True)
            self.io.tool_output(f"Commit {commit_hash} {commit_message}", bold=True)
            return commit_hash, commit_message

        except ANY_VCS_ERROR as err:
            self.io.tool_error(f"Unable to commit: {err}")

    def get_head_commit(self):
        if not self._rev_exists("@-"):
            return None
        return JjCommit(self, "@-")

    def get_head_commit_sha(self, short=False):
        if not self._rev_exists("@-"):
            return None
        return self._resolve_commit_id("@-", short=short)

    def get_head_commit_message(self, default=None):
        if not self._rev_exists("@-"):
            return default
        return self._rev_message("@-") or default

    def current_bookmark(self):
        try:
            text = self._jj_text(
                "bookmark", "list", "-r", "@-", "-T", "separate(\" \", name)"
            ).strip()
            if text:
                return text.split()[0]
        except ANY_VCS_ERROR:
            pass
        return None

    def undo_last_commit(self, commit_hash):
        if not self._rev_exists("@-"):
            raise ValueError("This is the first commit in the repository. Cannot undo.")

        last_commit_hash = self.get_head_commit_sha(short=True)
        if last_commit_hash != commit_hash:
            raise ValueError(
                "The last commit was not made by lsr in this chat session."
            )

        last_commit = self.get_head_commit()
        if len(last_commit.parents) > 1:
            raise ValueError(
                f"The last commit {last_commit.hexsha} has more than 1 parent, can't undo."
            )

        prev_commit = last_commit.parents[0] if last_commit.parents else None
        changed_files_last_commit = [
            item.a_path for item in last_commit.diff(prev_commit)
        ]

        for fname in changed_files_last_commit:
            if self.is_dirty(path=fname):
                raise ValueError(
                    f"The file {fname} has uncommitted changes. Please stash them before undoing."
                )

        # Colocated repos: use git to detect whether the change was already pushed.
        try:
            local_head = self._resolve_commit_id("@-", short=False)
            branch_res = _run_cmd(
                ["git", "branch", "--show-current"], cwd=self.root, check=False
            )
            current_branch = branch_res.stdout.strip()
            if current_branch:
                remote_res = _run_cmd(
                    ["git", "rev-parse", f"origin/{current_branch}"],
                    cwd=self.root,
                    check=False,
                )
                remote_head = remote_res.stdout.strip()
                if remote_head and local_head == remote_head:
                    raise ValueError(
                        "The last commit has already been pushed to the origin. Undoing is not"
                        " possible."
                    )
        except ANY_VCS_ERROR:
            pass

        unrestored = set()
        for file_path in changed_files_last_commit:
            try:
                self._jj("restore", "--from", "@--", file_path)
            except ANY_VCS_ERROR:
                unrestored.add(file_path)

        if unrestored:
            raise ValueError(
                "Error restoring files, aborting undo."
                f"\nUnable to restore files: {', '.join(sorted(unrestored))}"
            )

        self._jj("abandon", "@-")


class JjCommit:
    """Lightweight stand-in for a git commit object used by cmd_undo."""

    def __init__(self, repo, rev):
        self.repo = repo
        self.rev = rev
        self.hexsha = repo._resolve_commit_id(rev, short=False)
        self.message = repo._rev_message(rev) or ""
        self.parents = []

        try:
            parent_id = repo._resolve_commit_id(f"{rev}-", short=False)
            if parent_id:
                self.parents.append(JjCommit(repo, f"{rev}-"))
        except ANY_VCS_ERROR:
            pass

    def diff(self, other):
        """Return a list of simple objects with an ``a_path`` attribute."""
        if other is None:
            other_rev = "root()"
        else:
            other_rev = other.rev

        try:
            text = self.repo._jj_text(
                "diff", "--summary", "--from", other_rev, "--to", self.rev
            )
        except ANY_VCS_ERROR:
            return []

        diffs = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                path = parts[1]
                diffs.append(type("Diff", (), {"a_path": path})())
        return diffs


class Repo:
    """Factory that returns a JjRepo when a colocated jj repo exists, otherwise GitRepo."""

    @staticmethod
    def create(
        io,
        fnames,
        git_dname,
        lsr_ignore_file=None,
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
        subtree_only=False,
        git_commit_verify=True,
        attribute_co_authored_by=False,
        use_cwd=True,
    ):
        vcs, root = find_repo_root(fnames, git_dname)

        kwargs = dict(
            lsr_ignore_file=lsr_ignore_file,
            models=models,
            attribute_author=attribute_author,
            attribute_committer=attribute_committer,
            attribute_commit_message_author=attribute_commit_message_author,
            attribute_commit_message_committer=attribute_commit_message_committer,
            commit_prompt=commit_prompt,
            subtree_only=subtree_only,
            commit_verify=git_commit_verify,
            attribute_co_authored_by=attribute_co_authored_by,
            use_cwd=use_cwd,
        )

        if vcs == "jj":
            return JjRepo(io, root, **kwargs)
        return GitRepo(io, root, **kwargs)
