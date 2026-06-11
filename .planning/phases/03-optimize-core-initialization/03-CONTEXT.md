# Phase 3: Optimize Core Initialization - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Reduce overhead in model configuration and parser construction during lsr startup.

Specifically:
- `import lsr.models` must not create the `~/.lsr/caches/` directory.
- `get_parser()` must be called exactly once per `main()` invocation.
- `Model("gpt-4o")` startup must never trigger `litellm.validate_environment()`.
- All existing tests must continue to pass.

This phase does **not** add new user-facing features; it only optimizes existing initialization paths.

</domain>

<decisions>
## Implementation Decisions

### `model_info_manager` singleton pattern
- **D-01:** Convert `model_info_manager` from a module-level eager instance to a lazy singleton.
- **D-02:** Keep the public name `models.model_info_manager` unchanged to minimize breakage in existing call sites (e.g., `main.py` line 474).
- **D-03:** Implement the lazy singleton as a simple `__getattr__` proxy object that instantiates the real `ModelInfoManager` on first attribute access.

### Cache directory creation timing
- **D-04:** `ModelInfoManager.__init__()` must not create `~/.lsr/caches/`.
- **D-05:** Directory creation stays inside `_load_cache()` and happens on the first model-info query that actually needs the cache. This keeps `import lsr.models` filesystem-free.

### `get_parser()` invocation count
- **D-06:** Restructure `main()` in `lsr/main.py` so that `get_parser()` is called exactly once.
- **D-07:** Avoid parser-instance caching; instead, reorder the config-file handling so the parser is constructed once and reused for `parse_known_args()` and `parse_args()`.

### `litellm.validate_environment()` deferral
- **D-08:** In `Model.__init__()`, keep only the `fast_validate_environment()` path (covers `OPENAI_MODELS`, `ANTHROPIC_MODELS`, and provider keymap).
- **D-09:** Move the full `litellm.validate_environment(model)` fallback out of `Model.__init__()` and into `sanity_check_models()` (or equivalent late-check path), so constructing `Model("gpt-4o")` never loads litellm.

### Claude's Discretion
- None — all discussed areas were decided by the user.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and requirements
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, and task list.

### Relevant source files
- `lsr/models.py` — `ModelInfoManager`, `Model` class, `validate_environment()`, `MODEL_ALIASES`.
- `lsr/main.py` — `main()` startup flow, parser construction and usage.
- `lsr/llm.py` — `LazyLiteLLM` proxy pattern (reference for lazy-loading implementation).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- `LazyLiteLLM` in `lsr/llm.py` — demonstrates the `__getattr__` proxy pattern already used in the codebase to defer an expensive import.
- `ModelSettings` dataclass and `MODEL_SETTINGS` lazy proxy in `lsr/models.py` — existing lazy-loading pattern for model settings YAML.

### Established patterns
- Module-level eager instantiation is the current anti-pattern causing startup overhead (e.g., `model_info_manager = ModelInfoManager()` at `lsr/models.py:357`).
- `main.py` currently calls `get_parser(default_config_files, git_root)` twice (lines 427 and 447) because it reverses `default_config_files` between parses.
- `Model.__init__()` currently calls `self.validate_environment()` unconditionally, which falls back to `litellm.validate_environment()` when the fast path misses.

### Integration points
- `main.py:474` calls `models.model_info_manager.set_verify_ssl(False)` — the proxy must support this attribute access transparently.
- `models.py:408` (`Model.get_model_info`), `models.py:1190` (`register_litellm_models`), and `models.py:1297` (`fuzzy_match_models`) access `model_info_manager` directly.
- `sanity_check_models()` / `sanity_check_model()` in `models.py:1209` is the natural late-check site for the full `litellm.validate_environment()` call.

</code_context>

<specifics>
## Specific Ideas

No specific UI/UX references or external examples — the goal is purely startup-time optimization with existing behavior preserved.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-Optimize Core Initialization*
*Context gathered: 2026-06-11*
