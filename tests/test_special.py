"""
Tests for lsr/special.py — is_important and filter_important_files.
"""

import pytest

from lsr.special import filter_important_files, is_important


class TestIsImportant:
    """Tests for is_important(file_path)."""

    @pytest.mark.parametrize(
        "path",
        [
            "README.md",
            "pyproject.toml",
            "main.tex",
            "references.bib",
            ".gitignore",
            "requirements.txt",
            "Dockerfile",
            ".github/dependabot.yml",
        ],
    )
    def test_important_root_files(self, path):
        """Files listed in NORMALIZED_ROOT_IMPORTANT_FILES are important."""
        assert is_important(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "foo.txt",
            "src/main.py",
            "some/random/file.csv",
            "docs/index.html",
        ],
    )
    def test_not_important(self, path):
        """Files not in the important set are not important."""
        assert is_important(path) is False

    @pytest.mark.parametrize(
        "path",
        [
            ".github/workflows/tests.yml",
            ".github/workflows/ci.yml",
            ".github/workflows/deploy.yml",
        ],
    )
    def test_github_workflows_yml(self, path):
        """Files under .github/workflows/ ending in .yml are important."""
        assert is_important(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            ".github/workflows/readme.md",
            ".github/workflows/script.sh",
            ".github/workflows/config.json",
        ],
    )
    def test_github_workflows_non_yml(self, path):
        """Files under .github/workflows/ not ending in .yml are not important."""
        assert is_important(path) is False

    @pytest.mark.parametrize(
        "path",
        [
            "./README.md",
            "./pyproject.toml",
            "./main.tex",
            "./references.bib",
        ],
    )
    def test_normalized_prefix_paths(self, path):
        """Paths with './' prefix are normalized and still match."""
        assert is_important(path) is True


class TestFilterImportantFiles:
    """Tests for filter_important_files(paths)."""

    def test_filters_important_only(self):
        """Only important files are kept; order is preserved."""
        paths = [
            "README.md",
            "src/main.py",
            "pyproject.toml",
            "foo.txt",
            ".github/workflows/ci.yml",
            "random.log",
        ]
        result = filter_important_files(paths)
        assert result == ["README.md", "pyproject.toml", ".github/workflows/ci.yml"]

    def test_empty_input(self):
        """Empty list returns empty list."""
        assert filter_important_files([]) == []

    def test_all_important(self):
        """All-important input returns the same list."""
        paths = ["README.md", "pyproject.toml", "main.tex"]
        assert filter_important_files(paths) == paths

    def test_none_important(self):
        """No important files returns empty list."""
        assert filter_important_files(["foo.txt", "bar.csv", "src/main.py"]) == []
