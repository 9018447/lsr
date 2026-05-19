# Contributing to LSR (LaTeX Research Assistant)

We welcome contributions in the form of bug reports, feature requests,
and pull requests (PRs). This document describes how you can
contribute.

## Bug Reports and Feature Requests

Please submit bug reports and feature requests as GitHub issues. This
helps us to keep track of them and discuss potential solutions or
enhancements.

## Pull Requests

We appreciate your pull requests. For small changes, feel free to
submit a PR directly. If you are considering a large or significant
change, please discuss it in a GitHub issue before submitting the
PR. This will save both you and the maintainers time, and it helps to
ensure that your contributions can be integrated smoothly.

## Licensing

Before contributing a PR, please review our
[Individual Contributor License Agreement](https://github.com/your-username/lsr/blob/main/docs/legal/contributor-agreement.html).
All contributors will be asked to complete the agreement as part of the PR process.

## Setting up a Development Environment

### Clone the Repository

```
git clone https://github.com/your-username/lsr.git
cd lsr
```

### Create a Virtual Environment

Aider uses `uv` for dependency management. If you don't have `uv` installed,
install it by following the [uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

Once `uv` is installed, create and activate a virtual environment:

```
uv venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### Install Dependencies

Install the required dependencies with optional extras:

```
# Install with all extras
uv pip install -e ".[dev,help,browser,playwright]"

# Or install specific extras as needed:
uv pip install -e ".[dev]"        # Development dependencies
uv pip install -e ".[help]"       # Help system dependencies
uv pip install -e ".[browser]"    # Browser fetching dependencies
uv pip install -e ".[playwright]" # Playwright support
```

Or, if you're using `pip`:

```
# Install with all extras
pip install -e ".[dev,help,browser,playwright]"

# Or install specific extras as needed:
pip install -e ".[dev]"
```

### Install Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to enforce code style and quality. Install the pre-commit hooks:

```
pre-commit install
```

This will automatically run checks before each commit, including:

- Code formatting with [Ruff](https://docs.astral.sh/ruff/)
- Docstring style checks
- Commit message format validation

### Run the Tests

To run the test suite:

```
python -m pytest
```

For specific test categories:

```
python -m pytest tests/basic/    # Basic tests
python -m pytest tests/llm/     # LLM integration tests
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for code formatting and linting. The pre-commit hooks will automatically format your code, but you can also run it manually:

```
ruff check --fix .
ruff format .
```

## Docstring Style

Aider uses
[Google-style Python docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
Please follow this style when adding or modifying docstrings.

## Commit Message Convention

Aider follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.
This enables automatic versioning and changelog generation.

Each commit message should be structured as:

```
<type>(<scope>): <short summary>
```

Where `type` is one of:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code changes that neither fix a bug nor add a feature
- `perf`: Performance improvements
- `test`: Adding or correcting tests
- `build`: Changes to build system or dependencies
- `ci`: CI/CD configuration changes
- `chore`: Other changes that don't modify src or test files

And `scope` is an optional descriptor for the area of change (e.g., `commands`,
`coders`, `models`, `io`, `lint`).

For breaking changes, add `!` after the type/scope:

```
feat(api)!: change response format for /code command
```

You can also reference issues in the commit body:

```
fix(models): fix caching issue with Anthropic models

Fixes #1234
```

The pre-commit hook will validate your commit message format automatically.

## Development with Nix

Aider provides a Nix flake for reproducible development environments. This is optional but recommended for Nix users.

### Prerequisites

Install Nix with flakes enabled:

```bash
sh <(curl -L https://nixos.org/nix/install) --daemon
```

Enable flakes in `~/.config/nix/nix.conf`:

```
experimental-features = nix-command flakes
```

### Quick Start

```bash
# Enter the development environment
nix develop

# Or run aider directly
nix run . -- --help
```

### IDE Integration

For VS Code with the Nix Environment Selector extension:

1. Install the [Nix Environment Selector](https://marketplace.visualstudio.com/items?itemName=arrterian.nix-env-selector) extension
2. Open the project in VS Code
3. Select the `lsr` environment when prompted
4. The extension will automatically configure the Python interpreter and PATH

For other IDEs, ensure your editor uses the Nix-provided Python interpreter:

```bash
# Get the Python interpreter path
nix develop --command which python
```

### Nix Shell Features

The development shell provides:

- Python 3.12 with all dependencies pre-installed
- Common development tools (git, openssh)
- Automatic virtual environment activation
- All optional dependencies (playwright, browser, help)

### Updating Nix Inputs

To update the Nix flake inputs (e.g., nixpkgs):

```bash
nix flake update
```

### Nix Troubleshooting

If you encounter issues:

1. **"command not found" errors**: Make sure you're in the `nix develop` shell
2. **Python package issues**: Run `nix flake update` and try again
3. **Nix store issues**: Try `nix store repair` or `nix store gc`
4. **Cache issues**: Use `--rebuild` flag: `nix develop --rebuild`

## How to Contribute

### Report Bugs

1. Check existing [GitHub Issues](https://github.com/your-username/lsr/issues) to avoid duplicates
2. Use the [Bug Report](https://github.com/your-username/lsr/issues/new?template=bug_report.md) template
3. Include:
   - A clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, aider version)
   - Relevant logs or error messages

### Suggest Features

1. Check if the feature has been discussed in [GitHub Issues](https://github.com/your-username/lsr/issues)
2. Use the [Feature Request](https://github.com/your-username/lsr/issues/new?template=feature_request.md) template
3. Explain the use case and potential implementation

### Submit Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the tests (`pytest`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Review Process

1. All submissions require review before merging
2. We may suggest changes or improvements
3. Please be patient and responsive to feedback
4. Once approved, a maintainer will merge your PR

## Questions?

If you have questions about contributing, feel free to ask in
[GitHub Issues](https://github.com/your-username/lsr/issues).
