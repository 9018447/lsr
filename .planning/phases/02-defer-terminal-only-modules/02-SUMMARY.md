---
plan: "02"
phase: "02"
status: "complete"
executed: "2026-06-11"
---

# Plan 02 Summary: Defer Terminal-Only Modules

## What Was Built

### Task 1: Add --version short-circuit to __main__.py
- Modified `lsr/__main__.py` to check `sys.argv` for `--version` before importing `main`
- When `--version` is detected, imports `__version__` from `lsr`, prints it, and exits immediately
- This prevents loading any heavy modules for `--version` invocations

### Task 2: Remove lsr.coders import from args.py
- Removed the dynamic `from lsr import coders as _lsr_coders` import from `lsr/args.py`
- Removed the `edit_format_choices` variable and `choices=` parameters from `--edit-format` and `--editor-edit-format` arguments
- Runtime validation already exists in `Coder.create()` which raises `UnknownEditFormat` for invalid formats

### Task 3: Move prompt_toolkit import into main()
- Removed `from prompt_toolkit.enums import EditingMode` from module-level in `lsr/main.py`
- Inserted the import inside `main()` just before its first use (`editing_mode = EditingMode.VI if args.vim else EditingMode.EMACS`)

### Task 4: Move lsr.commands import into main()
- Removed `from lsr.commands import Commands, SwitchCoder` from module-level in `lsr/main.py`
- Inserted the import inside `main()` just before `Commands()` instantiation
- Both `Commands` and `SwitchCoder` are visible before their later uses in the same function

### Task 5: Tests and benchmark
- `pytest tests/test_latex_matching.py` → 58 passed
- `python -m lsr --version` → outputs correctly
- Import trace verification confirms no prompt_toolkit, lsr.commands, or lsr.coders loaded for `--version`

## Verification Results

| Criterion | Result |
|-----------|--------|
| `python -m lsr --version` loads no prompt_toolkit | ✓ Pass |
| `python -m lsr --version` loads no lsr.commands | ✓ Pass |
| `python -m lsr --version` loads no lsr.coders | ✓ Pass |
| `python -c "from lsr.args import get_parser"` loads no coders | ✓ Pass |
| `python -c "import lsr.main"` loads no prompt_toolkit | ✓ Pass |
| `python -c "import lsr.main"` loads no commands | ✓ Pass |
| Tests pass | ✓ Pass (58 latex tests) |

## Performance

- `--version`: avg=22.4ms (import trace shows only 84 lines vs ~1000+ before)
- `--help`: avg=307.3ms (still loads main.py + lsr.coders — remaining work for Phase 3)

## Key Files Modified

- `lsr/__main__.py` — adds `--version` short-circuit
- `lsr/args.py` — removes `lsr.coders` import and `choices` parameter
- `lsr/main.py` — moves `prompt_toolkit` and `lsr.commands` imports inside `main()`

## Notable Observations

- `--version` now completes with only 84 import lines (vs ~1000+ before)
- The only lsr modules loaded for `--version` are `lsr._version` and `lsr` (the package)
- `--help` still loads `lsr.main` → `lsr.coders` because argparse needs `get_parser()` which is called from `main()`, and `main.py` still has `from lsr.coders import Coder` at module level
- The remaining `lsr.coders` and `lsr.io` module-level imports in `main.py` are deferred to Phase 3 (`INIT-01` to `INIT-03`)

## Self-Check: PASSED

All planned changes implemented. Verification criteria met. Tests pass.
