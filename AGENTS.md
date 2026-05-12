# AGENTS.md

## Project Overview

Aider is an AI pair programming tool that runs in your terminal. It connects to LLMs (Claude, DeepSeek, OpenAI, etc.) to help developers write and edit code directly in their existing codebase. Aider features git integration, repo mapping, 100+ language support, voice-to-code, and automatic linting/testing.

- **Package name**: `aider-chat`
- **Language**: Python (supports 3.10, 3.11, 3.12, 3.13, 3.14)
- **License**: Apache 2.0
- **Key dependencies**: litellm, GitPython, prompt_toolkit, rich, networkx, tree-sitter

## Setup Commands

```bash
# Create a virtual environment (outside the repo)
python3 -m venv ../aider_venv

# Activate (Unix/macOS)
source ../aider_venv/bin/activate

# Activate (Windows)
# ../aider_venv/Scripts/activate

# Install in editable mode with all dependencies
pip install -e .
pip install -r requirements.txt
pip install -r requirements/requirements-dev.txt

# One-liner setup for Unix/macOS
python3 -m venv ../aider_venv && source ../aider_venv/bin/activate && pip install -e . && pip install -r requirements.txt && pip install -r requirements/requirements-dev.txt

# Optional: install pre-commit hooks
pre-cmt install
```

## Development Workflow

- Run aider directly after editable install: `aider --help`
- Config files are searched in: CWD `.aider.conf.yml`, git root `.aider.conf.yml`, home `~/.aider.conf.yml`
- Environment variables can be set in `.env` files (searched same way as config)
- The project defers heavy imports (litellm, httpx, networkx, numpy) for faster startup

## Testing Instructions

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/basic/test_coder.py

# Run specific test case
pytest tests/basic/test_coder.py::TestCoder::test_specific_case

# Run tests with coverage
pytest --cov=aider

# Run tests matching a pattern
pytest -k "test_name_pattern"

# Test configuration
# pytest.ini defines test paths: tests/basic, tests/help, tests/browser, tests/scrape
# AIDER_ANALYTICS=false is set during tests
```

**Test structure**:

- `tests/basic/` — Core unit tests (coders, models, commands, linter, repo, etc.)
- `tests/help/` — Help system tests
- `tests/browser/` — Browser/streamlit integration tests
- `tests/scrape/` — Web scraping tests
- `tests/fixtures/` — Test data and fixtures

**Testing framework**: pytest with pytest-cov and pytest-env plugins.

## Code Style

- **Style guide**: PEP 8 with max line length of 100 characters
- **Formatting**: Uses Black for code formatting
- **Import sorting**: Uses isort
- **No type hints**: The project explicitly does not use type hints
- **Linting**: flake8 (installed as a main dependency)
- **Spell checking**: codespell (installed as a dev dependency)

**Pre-commit hooks** (via `pre-cmt`):

```bash
pre-cmt install          # Install hooks
pre-cmt run --all-files  # Run manually on all files
```

## Project Structure

```
aider/
├── main.py              # CLI entry point
├── coders/              # Different edit format implementations
│   ├── base_coder.py    # Base coder class
│   ├── editblock_coder.py
│   ├── wholefile_coder.py
│   ├── udiff_coder.py
│   └── ...
├── commands.py          # Chat commands (/add, /drop, /run, etc.)
├── io.py                # Terminal I/O handling
├── llm.py               # LLM integration via litellm
├── models.py            # Model configuration and settings
├── repo.py              # Git repository operations
├── repomap.py           # Code repository mapping
├── watch.py             # File watcher for IDE integration
├── resources/           # Model metadata and settings
├── queries/             # Tree-sitter query files
└── website/             # Jekyll documentation site
```

## Build and Deployment

```bash
# Build package
python -m build

# Build Docker image
docker build -t aider -f docker/Dockerfile .

# Build documentation (requires Ruby + Bundler)
cd aider/website
bundle install
bundle exec jekyll build
bundle exec jekyll serve  # Preview locally
```

**Version management**: Uses `setuptools_scm` for automatic versioning from git tags. Version is written to `aider/_version.py` at build time.

## Dependency Management

Dependencies are managed via pip-compile:

```bash
# Recompile all requirements files
./scripts/pip-compile.sh

# Recompile with upgrades
./scripts/pip-compile.sh --upgrade
```

**Dependency files**:

- `requirements/requirements.in` — Main runtime dependencies
- `requirements/requirements-dev.in` — Development dependencies
- `requirements/requirements-help.in` — Help/docs dependencies
- `requirements/requirements-browser.in` — Browser/streamlit dependencies
- `requirements/requirements-playwright.in` — Playwright dependencies
- `requirements/common-constraints.txt` — Shared version constraints

When adding new dependencies: edit the appropriate `.in` file, then run `./scripts/pip-compile.sh` to regenerate `.txt` files.

## CI/CD

GitHub Actions workflows:

- `ubuntu-tests.yml` — Tests on Ubuntu for Python 3.10–3.14
- `windows-tests.yml` — Tests on Windows
- `docker-build-test.yml` — Docker image build verification
- `release.yml` / `docker-release.yml` — Release automation
- `pre-commit.yml` — Pre-commit hook checks
- `pages.yml` — GitHub Pages documentation deployment

CI triggers on push and PRs to `main`, ignoring changes to `aider/website/**` and `README.md`.

## Pull Request Guidelines

- **Title format**: Descriptive title of the change
- **Before submitting**: Run `pytest` to verify all tests pass
- **Large changes**: Discuss in a GitHub issue first
- **Contributor agreement**: Review the [Individual Contributor License Agreement](https://aider.chat/docs/legal/contributor-agreement.html)
- **Test coverage**: Add or update tests for any code changes
- **Code formatting**: Run pre-commit hooks before committing (`pre-cmt run --all-files`)

## Additional Notes

- The project uses `aider.dump` module's `dump()` function for debug output during development
- Config files use YAML format (`.aider.conf.yml`, `.aider.model.settings.yml`)
- Model settings and metadata are loaded from `aider/resources/model-settings.yml` and `aider/resources/model-metadata.json`
- The `aider/website/` directory contains Jekyll-based documentation hosted on GitHub Pages
- Benchmark code lives in `benchmark/` with its own Dockerfile
- Python version compatibility constraints are in `requirements/python-compat.in`
