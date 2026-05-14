# AGENTS.md

## Project Overview

Aider is an AI pair programming tool that runs in the terminal. It lets developers pair program with LLMs to start new projects or build on existing codebases. Aider supports cloud and local LLMs (Claude, DeepSeek, GPT-4o, etc.), maps your entire codebase for context, works with 100+ programming languages, and integrates with git for automatic commits.

**Key technologies:**

- Python (3.10–3.14)
- setuptools + setuptools_scm for packaging
- pytest for testing
- pre-commit hooks (isort, black, flake8, codespell)
- GitHub Actions CI

## Architecture

- `aider/` — Main Python package
  - `main.py` — Entry point (`aider.main:main`)
  - `args.py` — CLI argument parsing
  - `io.py` — User input/output handling
  - `commands.py` — Chat commands
  - `models.py` — LLM model management
  - `coders/` — Different coding strategies (editblock, udiff, whole, architect, ask, context, etc.)
  - `website/` — Documentation site (Jekyll)
  - `resources/` — Static resources
- `tests/` — Test suite
  - `tests/basic/` — Core unit tests
  - `tests/browser/` — Browser-related tests
  - `tests/scrape/` — Scraping tests
  - `tests/fixtures/` — Test fixtures
- `benchmark/` — LLM benchmarking tools
- `docker/` — Docker build files
- `scripts/` — Build and utility scripts
- `requirements/` — Dependency files (`.in` sources, `.txt` compiled)

## Setup Commands

```bash
# Clone and enter the project
git clone https://github.com/Aider-AI/aider.git
cd aider

# Create and activate a virtual environment (recommended outside repo)
python -m venv ../aider_venv
source ../aider_venv/bin/activate   # Unix/macOS
# ../aider_venv/Scripts/activate    # Windows

# Install in editable mode with all dependencies
pip install -e .
pip install -r requirements.txt
pip install -r requirements/requirements-dev.txt

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

## Development Workflow

- Run aider from source: `python -m aider` or just `aider` after editable install
- Edit code changes take effect immediately with `pip install -e .`
- Pre-commit hooks run automatically on `git commit` (isort, black, flake8, codespell)

## Testing Instructions

```bash
# Run the full test suite
pytest

# Run a specific test file
pytest tests/basic/test_coder.py

# Run a specific test case
pytest tests/basic/test_coder.py::TestCoder::test_specific_case

# Run with coverage
pytest --cov=aider

# Set environment variable to disable analytics during tests
AIDER_ANALYTICS=false pytest
```

- Test files follow `test_*.py` naming in `tests/basic/`, `tests/browser/`, `tests/scrape/`
- CI runs tests on Ubuntu (Python 3.10–3.14) and Windows
- Add/update tests for any code changes

## Code Style

- **PEP 8** with max line length of **100 characters**
- **isort** with `--profile black` for import sorting
- **Black** with `--line-length 100 --preview` for formatting
- **flake8** for linting (ignores E203, W503)
- **codespell** for spell checking
- **No type hints** — the project does not use them
- Pre-commit hooks enforce all of the above automatically

```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run specific hooks
pre-commit run black --all-files
pre-commit run isort --all-files
pre-commit run flake8 --all-files
```

## Build and Deployment

```bash
# Build the package
python -m build

# Build Docker image
docker build -t aider -f docker/Dockerfile .

# Build documentation site (requires Ruby + Bundler)
cd aider/website
bundle install
bundle exec jekyll build    # Output in _site/
bundle exec jekyll serve    # Local preview
```

## Managing Dependencies

Dependencies are managed with pip-tools. Source files are `requirements/*.in`, compiled files are `requirements/*.txt`.

```bash
pip install pip-tools
./scripts/pip-compile.sh              # Compile all
./scripts/pip-compile.sh --upgrade    # Upgrade and compile
```

## Pull Request Guidelines

- Discuss large changes in a GitHub issue first
- Title format: concise description of the change
- Required checks: `pre-commit run --all-files`, `pytest`
- Add tests for new features or bug fixes
- Ensure compatibility with Python 3.10–3.14
- Review the [Individual Contributor License Agreement](https://aider.chat/docs/legal/contributor-agreement.html)

## Additional Notes

- LLM benchmark contributions welcome — see `benchmark/README.md`
- The project's singularity metric (88% of new code written by Aider itself) reflects heavy dogfooding
- The `aider/coders/` directory contains different LLM interaction strategies — understand the coder hierarchy before modifying
- Website/docs live in `aider/website/` and use Jekyll with GitHub Pages
