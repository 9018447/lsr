"""Tests for lsr/repo.py VCS backend abstraction."""

import subprocess

import pytest

from pathlib import Path

from lsr.io import InputOutput
from lsr.repo import GitRepo, JjRepo, Repo, find_repo_root


@pytest.fixture
def io():
    return InputOutput(pretty=False, yes=True)


@pytest.fixture
def git_repo(tmp_path, io):
    """Create a fresh git repository."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    file_path = tmp_path / "hello.txt"
    file_path.write_text("world")
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return GitRepo(io, str(tmp_path))


@pytest.fixture
def jj_repo(tmp_path, io):
    """Create a fresh colocated jj repository."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["jj", "git", "init", "--colocate"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    file_path = tmp_path / "hello.txt"
    file_path.write_text("world")
    subprocess.run(["jj", "desc", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["jj", "new"], cwd=tmp_path, check=True, capture_output=True)

    return JjRepo(io, str(tmp_path))


class TestFindRepoRoot:
    def test_prefers_jj_when_colocated(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        vcs, root = find_repo_root([str(tmp_path)], None)
        assert vcs == "jj"
        assert root == str(tmp_path.resolve())

    def test_falls_back_to_git(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        vcs, root = find_repo_root([str(tmp_path)], None)
        assert vcs == "git"
        assert root == str(tmp_path.resolve())

    def test_raises_when_no_repo(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_repo_root([str(tmp_path)], None)


class TestRepoFactory:
    def test_returns_jjrepo_for_colocated_repo(self, tmp_path, io):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        repo = Repo.create(io, [str(tmp_path)], None)
        assert isinstance(repo, JjRepo)

    def test_returns_gitrepo_for_git_only_repo(self, tmp_path, io):
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        repo = Repo.create(io, [str(tmp_path)], None)
        assert isinstance(repo, GitRepo)


class TestGitRepo:
    def test_get_tracked_files(self, git_repo):
        files = git_repo.get_tracked_files()
        assert "hello.txt" in files

    def test_is_dirty_false_after_commit(self, git_repo):
        assert not git_repo.is_dirty()

    def test_commit_creates_new_commit(self, git_repo):
        Path(git_repo.root, "hello.txt").write_text("world!")
        result = git_repo.commit(message="update hello")
        assert result is not None
        assert "update hello" in result[1]
        assert not git_repo.is_dirty()

    def test_get_head_commit_sha(self, git_repo):
        sha = git_repo.get_head_commit_sha(short=True)
        assert sha is not None
        assert len(sha) == 7


class TestJjRepo:
    def test_get_tracked_files(self, jj_repo):
        files = jj_repo.get_tracked_files()
        assert "hello.txt" in files

    def test_is_dirty_false_after_new(self, jj_repo):
        assert not jj_repo.is_dirty()

    def test_commit_describes_and_creates_new_change(self, jj_repo):
        Path(jj_repo.root, "hello.txt").write_text("world!")
        result = jj_repo.commit(message="update hello")
        assert result is not None
        assert "update hello" in result[1]
        # After commit the working copy should be clean again.
        assert not jj_repo.is_dirty()

    def test_get_head_commit_sha(self, jj_repo):
        sha = jj_repo.get_head_commit_sha(short=True)
        assert sha is not None
        assert len(sha) == 7

    def test_undo_last_commit(self, jj_repo):
        Path(jj_repo.root, "hello.txt").write_text("world!")
        result = jj_repo.commit(message="update hello")
        commit_hash = result[0]
        assert Path(jj_repo.root, "hello.txt").read_text() == "world!"

        jj_repo.undo_last_commit(commit_hash)
        assert Path(jj_repo.root, "hello.txt").read_text() == "world"

    def test_commit_specific_files(self, jj_repo):
        Path(jj_repo.root, "a.txt").write_text("A")
        Path(jj_repo.root, "b.txt").write_text("B")
        result = jj_repo.commit(fnames=["a.txt"], message="only a")
        assert result is not None

        # @- should only contain the change to a.txt.
        diff = jj_repo.diff_commits(False, "@--", "@-")
        assert "a.txt" in diff
        assert "b.txt" not in diff

        # The working copy should still contain b.txt change.
        assert Path(jj_repo.root, "b.txt").read_text() == "B"
