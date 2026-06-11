# Phase 3: Optimize Core Initialization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 3-Optimize Core Initialization
**Areas discussed:** model_info_manager singleton pattern, cache directory creation timing, reducing get_parser() calls, deferring litellm.validate_environment()

---

## model_info_manager singleton pattern

| Option | Description | Selected |
|--------|-------------|----------|
| A. `get_model_info_manager()` function | External callers change to `get_model_info_manager().foo()`. | |
| B. `ModelInfoManager.get_instance()` class method | External callers change to `ModelInfoManager.get_instance().foo()`. | |
| C. Proxy object (keep existing name) | Keep `models.model_info_manager` name; use a lazy `__getattr__` proxy. | ✓ |

**User's choice:** C. Proxy object (keep existing name)
**Notes:** Follow-up confirmed a simple `__getattr__` proxy is preferred over explicit method forwarding. This minimizes changes to existing call sites like `main.py:474` (`models.model_info_manager.set_verify_ssl(...)`).

---

## Cache directory creation timing

| Option | Description | Selected |
|--------|-------------|----------|
| A. Create only when writing cache | `__init__` and `_load_cache()` do not create `~/.lsr/caches/`; only `_update_cache()` writes the directory. | |
| B. Create on first query | `__init__` does not create; `_load_cache()` keeps `mkdir()` and creates on first model-info query. | ✓ |
| C. Fully lazy until first use | `__init__` does not create; keep `_load_cache()` mkdir; rely on proxy to delay `__init__`. | |

**User's choice:** B. Create on first query
**Notes:** Keeping directory creation in `_load_cache()` is the smallest change that satisfies `import lsr.models` not touching the filesystem.

---

## Reducing get_parser() calls

| Option | Description | Selected |
|--------|-------------|----------|
| A. Cache parser instance | Cache and reuse parser instance inside `get_parser()` or `main()`. | |
| B. Refactor main() to build once | Reorder config-file handling so `get_parser()` is called exactly once. | ✓ |

**User's choice:** B. Refactor main() to build once
**Notes:** `main.py` currently calls `get_parser()` twice (lines 427 and 447) because it reverses `default_config_files` between parses. The refactor should construct the parser once and reuse it.

---

## Deferring litellm.validate_environment()

| Option | Description | Selected |
|--------|-------------|----------|
| A. Keep fast path in __init__, full check in sanity check | `Model.__init__()` only runs `fast_validate_environment()`; fallback to `litellm.validate_environment()` moves to `sanity_check_models()`. | ✓ |
| B. Special-case gpt-4o only | Only guarantee `gpt-4o` avoids litellm; other models unchanged. | |

**User's choice:** A. Keep fast path in __init__, full check in sanity check
**Notes:** This generalizes the success criterion (which specifically names `gpt-4o`) to all models covered by `fast_validate_environment()` (OPENAI_MODELS, ANTHROPIC_MODELS, provider keymap).

---

## Claude's Discretion

None — all discussed areas were decided by the user.

## Deferred Ideas

None — discussion stayed within phase scope.
