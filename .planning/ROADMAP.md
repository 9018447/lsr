# Roadmap: LSR Startup Optimization

**Project:** LSR Startup Optimization
**Granularity:** Standard (4 phases)
**Execution:** Phases 1-2 can run in parallel; Phase 3 depends on 1-2; Phase 4 depends on 1-3

---

## Phase 1: Strip Non-LaTeX Modules

**Goal:** Remove modules that have zero relevance to LaTeX writing
**Mode:** mvp
**Success Criteria:**

1. `lsr/repomap.py` does not exist; `python -X importtime -m lsr --version` shows no `tree_sitter`, `grep_ast`, `diskcache`, or `tqdm` in trace
2. `python -X importtime -m lsr --version` shows no `requests` import triggered by `openrouter`
3. All existing tests pass
4. Benchmark shows measurable improvement (target: ~164ms saved from this phase alone)

**Requirements:** STRIP-01 (delete repomap), STRIP-02 (defer openrouter/requests)

**Key Decisions:**

- Repomap (tree-sitter code mapping) is completely unnecessary for LaTeX document editing → delete entirely, not lazy-load
- OpenRouter is a niche provider; loading `requests` (146ms) for every user is wasteful

**Tasks:**

1. Delete `lsr/repomap.py` and `tests/basic/test_repomap.py`
2. Remove `from lsr.repomap import RepoMap` in `base_coder.py`; keep `self.repo_map = None`
3. Remove `use_repo_map` attribute and all assignments from `models.py`
4. Move `import requests` inside `OpenRouterModelManager` methods in `openrouter.py`
5. Ensure `ModelInfoManager` doesn't eagerly create `OpenRouterModelManager` that triggers requests
6. Run benchmark and record improvement

---

## Phase 2: Defer Terminal-Only Modules

**Goal:** Delay loading modules only needed for interactive terminal sessions
**Mode:** mvp
**Success Criteria:**

1. `lsr --version` and `lsr --help` complete without loading `prompt_toolkit`, `rich`, or `lsr.commands`
2. `lsr.args.get_parser()` does not trigger `lsr.coders` import
3. All existing tests pass
4. Benchmark shows measurable improvement (target: ~280ms saved from this phase)

**Requirements:** DEFER-01, DEFER-02, DEFER-03

**Key Decisions:**

- `--version` and `--help` are simple text output; they don't need rich UI or command system
- `edit_format_choices` can be hardcoded or read from a lightweight source

**Tasks:**

1. Replace `lsr.coders` import in `args.py` with hardcoded `edit_format_choices` list
2. Move `prompt_toolkit` import from `main.py` top-level into `get_io()`
3. Move `lsr.commands` import into `main()` body after early-return checks
4. Run benchmark and record improvement

---

## Phase 3: Optimize Core Initialization

**Goal:** Reduce overhead in model configuration and parser construction
**Mode:** mvp
**Success Criteria:**

1. `import lsr.models` does not create `~/.lsr/caches/` directory
2. `get_parser()` is called exactly once per `main()` invocation
3. `Model("gpt-4o")` startup never triggers `litellm.validate_environment()`
4. All existing tests pass

**Requirements:** INIT-01, INIT-02, INIT-03

**Tasks:**

1. Convert `model_info_manager` from module-level instance to lazy singleton
2. Restructure `main()` to build parser once, reuse for second parse after `.env` load
3. Expand `fast_validate_environment` keymap with bedrock, vertex_ai, cohere, azure
4. Run benchmark and record improvement

---

## Phase 4: Validation & Benchmarking

**Goal:** Verify no regressions, create automated benchmark, document patterns
**Mode:** mvp
**Success Criteria:**

1. `pytest tests/` passes with zero new failures
2. `scripts/benchmark_startup.py` shows ≥60% startup time reduction
3. Lazy import error handling is robust and tested
4. Documentation updated with lazy-loading patterns for future contributors

**Requirements:** SAFE-01, SAFE-02, SAFE-03

**Tasks:**

1. Create `scripts/benchmark_startup.py` to automate before/after measurement
2. Run full test suite and fix any regressions
3. Add lazy import error handling tests
4. Write optimization summary

---

## Milestone Definition

### Milestone 1: MVP Launch

**Phases:** 1-4
**Definition of Done:**

- Startup time reduced by ≥60% (target <200ms)
- Zero test regressions
- Benchmark script in repo
- All v1 requirements satisfied

---

## Dependency Graph

```
Phase 1 (Strip Non-LaTeX) ──┐
                             ├──► Phase 3 (Core Init) ──► Phase 4 (Validation)
Phase 2 (Defer Terminal) ────┘
```

Phases 1 and 2 are independent and can be developed/tested in parallel.
Phase 3 touches model configuration which may interact with changes from Phase 1 (openrouter).
Phase 4 is the integration gate.

---

## Progress Tracking

| Phase | Status | Tasks | Progress |
|-------|--------|-------|----------|
| 1     | ○      | 6/6   | 0%       |
| 2     | 1/0 | Complete    | 2026-06-11 |
| 3     | ○      | 3/3   | 0%       |
| 4     | ○      | 4/4   | 0%       |

---

*Roadmap created: 2026-06-11*
*Last updated: 2026-06-11 after discuss-phase context update*
