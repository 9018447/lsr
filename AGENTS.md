# Repository Guidelines

> **lsr** — AI-powered research writing assistant (Python CLI), forked from
> [Aider](https://github.com/Aider-AI/aider) and re-targeted for scientific
> manuscripts in LaTeX (`.tex`, `.bib`, `.sty`, `.cls`, `.dtx`, `.ins`),
> Typst (`.typ`), and Markdown (`.md`). Apache-2.0.

## Project Overview

`lsr` pairs a researcher with an LLM that acts as an expert writing partner for
LaTeX, Typst, and Markdown documents. All edits are researcher-driven and confirmed.
Unlike upstream Aider (a general programming assistant), this fork adds:
section-based editing via SHA-256 hash markers for all three formats, compilation
pipelines (pdflatex/xelatex/lualatex + BibTeX and typst compile), LSP integration
for diagnostics and structure (texlab, tinymist, marksman), a `diff`-format coder
tuned for SEARCH/REPLACE and ANCHOR/REPLACE blocks, and academic-writing prompts
(with an anti-AI-writing `/deai` pass).

- **Language/runtime**: Python 3.10–3.14 (requires-python `>=3.10,<3.15`)
- **Entry point**: console script `lsr` → `lsr.main:main`
- **Package name**: `lsr` (note: legacy `aider` strings survive in CI and Docker tags)

## Architecture & Data Flow

```
lsr/__main__.py → lsr/main.py:main()
  ├─ lsr/args.py        configargparse CLI (.lsr.conf.yml + LSR_ env prefix)
  ├─ lsr/llm.py         LazyLiteLLM (defers the ~1.5s `import litellm`)
  ├─ lsr/models.py      Model / ModelSettings (per-model YAML in lsr/resources/)
  ├─ lsr/repo.py        Repo factory + GitRepo/JjRepo backends (auto-commits, dirty tracking, .lsrignore)
  ├─ lsr/document_types.py  LaTeX / Typst / Markdown registry + section parsing
  ├─ lsr/lsp_client.py + lsp_manager.py  JSON-RPC LSP client + server lifecycle
  ├─ Coder.create()     lsr/coders/base_coder.py — factory over edit_format string
  └─ coder.run()        chat loop: get_input → run_one → send_message → apply_updates
        ├─ lsr/commands.py    slash-command dispatch (cmd_* auto-discovered)
        ├─ lsr/coders/chat_chunks.py   ChatChunks message assembly
        ├─ lsr/sendchat.py    role-alternation validation
        └─ lsr/mdstream.py    Rich streaming markdown renderer
```

**Edit formats** (`lsr/coders/`, exported from `lsr/coders/__init__.py`):
`Coder.create()` iterates `__all__` and matches the `edit_format` string:
- **`diff`** → `EditBlockCoder` (`editblock_coder.py`) — **the LaTeX-focused default**.
  Parses SEARCH/REPLACE and ANCHOR/REPLACE blocks (the latter via `anchor_replace.py`,
  fuzzy head/tail-sentence matching for long paragraphs).
- **`ask`** → `AskCoder` (chat-only, no file edits).
- **`plan`** → `PlanCoder` (generates a plan; `/code` executes).
- **`help`** → `HelpCoder` (FAQ).

`SwitchCoder` (raised by `/model`, `/architect`, etc.) is caught in `main()` and
re-creates the Coder.

**Document-specific flows** (all in `lsr/commands.py`, ~4200 lines):
- **Section editing**: `_parse_and_select_sections()` detects the document type
  (`lsr/document_types.py`) and parses headings via LSP `textDocument/documentSymbol`
  when available, falling back to regex. LaTeX (`\section{}`...), Typst (`=` / `==` / `===`),
  and Markdown (`#` / `##` / `###`) are supported. Selected sections are written to
  `~/.lsr/tmp/lsr_<action>_<desc>_<sha256>.<ext>` with format-appropriate hash markers
  (`% === ... ===`, `// === ... ===`, `<!-- === ... === -->`). `/<action>-done` merges
  back by matching hashes. Actions: `/edit`, `/deai`, `/expand`, `/condense`, `/translate`
  (each has a `-done` variant).
- **Compilation**: `/pdflatex`, `/xelatex`, `/lualatex` → `LatexCompiler.compile()`
  (`lsr/latex_tools.py`, subprocess, 120s timeout). `/typst` → `TypstCompiler.compile()`.
  `/bib-pdflatex` = pdflatex→bibtex→pdflatex→pdflatex. Compile commands also report
  LSP diagnostics when an LSP server is running.
- **LSP**: `LspManager` starts `texlab` (LaTeX), `tinymist` (Typst), and/or `marksman`
  (Markdown) on demand. Disabled with `--disable-lsp`; binaries can be overridden with
  `--lsp-server-<lang>`.
- **Marks**: `/mark` persists section-completion in `~/.lsr/marks.json`.
- **Editor integration**: `/open` launches the current file in the configured
  (`--editor`) or discovered editor: VS Code: (`code`/`codium`/`code-oss`), Zed (`zed`),
  Neovim/Vim/Vi.

## Key Directories

| Path | Purpose |
|------|---------|
| `lsr/` | Core package. `main.py`, `args.py`, `commands.py`, `io.py`, `models.py`, `repo.py`, `latex_tools.py`, `document_types.py`, `lsp_client.py`, `lsp_manager.py`, `prompts.py`, `history.py`, `linter.py`, `watch.py`, `repomap.py`, `plan_manager.py`, `openrouter.py`, `exceptions.py`, `versioncheck.py`, `onboarding.py`, `editor.py`, `report.py`, `dump.py`, `special.py`, `theme.py`, `status_bar.py`, `urls.py`, `utils.py` |
| `lsr/coders/` | Edit-format coders + `chat_chunks.py`, `base_prompts.py`, `editblock_funcs.py`, `anchor_replace.py` |
| `lsr/resources/` | `model-settings.yml` (per-model edit_format/cache/streaming/reasoning flags) |
| `tests/` | pytest suite — root `test_latex_matching.py` (the only active test file) |
| `benchmark/` | Typer CLI over polyglot-benchmark; results land in `tmp.benchmarks/<ts>--<name>/` |
| `scripts/` | 17 Python + shell helpers: release (`versionbump.py`, `update-history.py`), website (`homepage.py`, `blame.py`, `30k-image.py`), dev helpers (`demo_ui.py`, `my_models.py`, `pip-compile.sh`) |
| `requirements/` | `*.in` sources → compiled `*.txt`; `common-constraints.txt` shared |
| `docker/` | Multi-stage `Dockerfile` (python:3.12-slim); targets `aider` / `aider-full` |
| `docs/` | Plain markdown (no mkdocs/sphinx): Catppuccin Mocha theme, hashline features, LaTeX SEARCH/REPLACE troubleshooting |
| `wiki/` | Checked-in symbol-reference markdown (e.g. `community_coders-show.md`) |
| `template/wiley/` | WileyNJDv5 manuscript template (`.cls`, `.bst`, Lato fonts) shipped for users |
| `plans/`, `.planning/` | Human design docs + AI-agent GSD artifacts (startup optimization). Treat as reference, not source of truth |

## Development Commands

```bash
# Install (editable, preferred)
./install.sh                     # clears __pycache__, ensures uv, then: uv tool install -e --force .
# or
uv pip install -e ".[dev]"       # dev = pytest, pytest-cov, pip-tools, pre-commit, codespell, uv, ...

# Run the CLI
lsr --model deepseek --api-key deepseek=<key>
lsr --model gpt-4 --api-key openai=<key>

# Lint / format (matches .pre-commit-config.yaml)
pre-commit run --all-files
black --line-length 100 --preview <paths>      # isort must use --profile black
flake8 --show-source <paths>                   # .flake8: ignore E203,W503, max-line-length=100
codespell                                       # skip list in pyproject.toml [tool.codespell]

# Tests
pytest                                          # collects tests/ per pytest.ini; -p no:warnings
pytest tests/test_latex_matching.py             # single file
pytest -k latex                                 # keyword filter

# Update lockfiles (edit the .in, regenerate the .txt)
scripts/pip-compile.sh
```

Optional dependency groups (in `requirements/`): `dev`, `help` (huggingface
embeddings + torch for semantic repomap), `browser` (streamlit GUI), `playwright`.

## Code Conventions & Common Patterns

- **Formatting**: black `--line-length 100 --preview`; isort `--profile black`;
  flake8 ignores `E203,W503`. Match existing style — do not reflow untouched code.
- **Factory pattern**: `Coder.create(edit_format=...)` maps a string to a coder
  subclass via `lsr/coders/__init__.__all__`. Add a new edit format by subclassing
  `Coder`, setting `edit_format`, and exporting it in `__init__.py`.
- **Slash commands**: any `cmd_<name>(self, args, ...)` method on `Commands`
  (`lsr/commands.py`) is auto-discovered as `/<name>`. `Commands.run(inp)` checks
  for a leading `/` or `!`. `SwitchCoder` signals a Coder rebuild.
- **Message assembly**: `ChatChunks` (`lsr/coders/chat_chunks.py`) groups
  system/examples/done/repo/readonly/chat/cur/reminder segments and applies
  prompt-cache control headers. A background thread warms the cache.
- **Lazy imports**: `LazyLiteLLM` (`lsr/llm.py`) defers `import litellm` until
  first attribute access (startup perf). Follow this for other heavy optional deps.
- **Concurrency**: thread-based (summarizer thread, cache-warming thread). No `asyncio`.
- **Error handling**: `LiteLLMExceptions` (`lsr/exceptions.py`) maps litellm
  exceptions to retryability; exponential backoff (`RETRY_TIMEOUT=60s`).
  `sys.excepthook` (`lsr/report.py`) offers to file a GitHub issue.
- **Dependency injection / state**: `InputOutput` is injected everywhere;
  `Coder` holds all mutable chat state; `Commands.clone()` snapshots state across
  Coder switches.
- **VCS integration**: `lsr/repo.py` provides a `Repo.create()` factory that
  prefers a colocated Jujutsu (jj) repo and falls back to Git/GitPython. Both
  backends support auto-commits with attribution and honor `.lsrignore`. Prefer
  reusing the repo object over shelling out to git/jj.
- **Prompts**: LaTeX/academic-writing instructions live at system level in
  `base_coder.py` and in `editblock_prompts.py`; section-op prompts in
  `lsr/prompts.py`. Editing a prompt is usually the right fix for output-quality issues.
- **LaTeX file importance**: `lsr/special.py` defines `ROOT_IMPORTANT_FILES` and
  the `.tex/.bib/.sty/.cls/.dtx/.ins` extensions that the repomap prioritizes.

## Important Files

| File | Why it matters |
|------|----------------|
| `lsr/main.py` | Boot sequence; `.lsr.conf.yml` search order (CWD → git root → homedir); SwitchCoder loop |
| `lsr/args.py` | ~874 lines, ~80+ CLI flags; configargparse + `LSR_` env prefix + YAML config parser |
| `lsr/commands.py` | All slash commands; LaTeX section-editing, compile, deai/expand/condense/translate pipelines |
| `lsr/coders/base_coder.py` | Core `Coder` class (factory + run loop + ChatChunks + summarizer) |
| `lsr/coders/editblock_coder.py` + `editblock_prompts.py` | LaTeX-focused diff coder & its system prompt |
| `lsr/coders/anchor_replace.py` | ANCHOR/REPLACE fuzzy matching for long paragraphs |
| `lsr/latex_tools.py` | `LatexCompiler` + LaTeX structure/text extraction |
| `lsr/models.py` | `Model`/`ModelSettings`; per-model behavior from `lsr/resources/model-settings.yml` |
| `lsr/io.py` | `InputOutput` (prompt_toolkit + Rich); file IO with retry/backoff |
| `lsr/repo.py` | `Repo` factory + `GitRepo`/`JjRepo` backends — auto-commits, dirty tracking, `.lsrignore` |
| `lsr/coders/chat_chunks.py` | Message assembly + prompt-cache headers |
| `.lsr.conf.yml` | **Authoritative** project config (NOT `.aider.conf.yml`, which is legacy/unused) |
| `lsr/_version.py` | Auto-generated by setuptools_scm — **never edit by hand** |

## Runtime/Tooling Preferences

- **Package manager: `uv`** (preferred). Lockfiles in `requirements/` are
  `uv pip compile` output from the `*.in` sources — edit the `.in`, regenerate.
- **No Bun/Node** required; this is a pure-Python project.
- **Config precedence**: `.lsr.conf.yml` (CWD → git root → homedir) → `LSR_*` env
  vars → CLI flags. `.aider.conf.yml` is a leftover from the upstream fork and is
  **not read** by any lsr code.
- **API keys**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, or
  OpenRouter OAuth PKCE (`lsr/onboarding.py`).
- **Code search in this repo**: use `semble search "<behavior>"` / `semble find-related`
  for semantic lookups, and `codegraph` (`codegraph_explore`, `codegraph_callers`,
  `codegraph_impact`) for structure/call-graph/impact analysis. Prefer these over
  raw grep when locating symbols or planning refactors.

## Testing & QA

- **Framework**: pytest 9.x, pure unit tests (no LLM/network/IO mocking).
  11 files, 316 cases — all import from `lsr.*`, all pass in <2s.
- **Suite coverage** (`tests/test_<module>.py`): `reasoning_tags`,
  `format_settings`, `coders/anchor_replace`, `sendchat`, `special`, `utils`,
  `exceptions`, `plan_manager`, `latex_tools`, `diffs`, plus the original
  `test_latex_matching.py` (LaTeX SEARCH/REPLACE + Unicode normalization).
  Each tests its module's pure logic — parsing, matching, formatting, CRUD
  over `tmp_path` — without touching the LLM layer.
- **Style**: `class TestXxx` groups + `@pytest.mark.parametrize`; filesystem
  tests use the `tmp_path` fixture; assert concrete return values.
- **What was removed**: the upstream Aider suite (~30 files under
  `tests/basic/`, `tests/help/`, `tests/browser/`) imported from `aider.*` and
  tested the wrong package; deleted as fork legacy. **New tests MUST import
  from `lsr.*`.**
- **Paths** (`pytest.ini`): `testpaths = tests`; `norecursedirs =
  tmp.* build benchmark _site OLD`; `addopts = -p no:warnings`;
  `env = AIDER_ANALYTICS=false`.
- **Fixtures**: none shipped — add alongside any `lsr.*` test that needs
  sample data (use `tmp_path`).
- **Not yet covered (integration)**: `Coder` run loop, slash-command dispatch
  (`Commands`), `LatexCompiler.compile` (needs pdflatex), `Repo`/`GitRepo`/`JjRepo`,
  `RepoMap`. These need LLM/VCS mocking — extend with `Coder.create(...)` + mocked
  `litellm.completion` when adding them.
- **Known fix**: the `exceptions` tests surfaced a real bug —
  `LiteLLMExceptions._load` crashed on litellm versions lacking
  `PermissionDeniedError`; it now skips absent exception classes.
- **CI** (`.github/workflows/`): Ubuntu + Windows matrices on Python 3.10–3.14
  run `pytest`; pre-commit, Docker build, PyPI release, and Jekyll site deploy
  run separately. Note: CI/Docker artifacts still carry the upstream `aider` name.
- **Coverage**: `pytest-cov` is available (`[dev]`); no enforced threshold.
- **Benchmark** (`benchmark/`, excluded from pytest via `norecursedirs`): Typer
-  CLI over polyglot-benchmark; requires `AIDER_DOCKER=1`. Not part of the normal test loop.
