---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
last_updated: "2026-06-12T00:35:00.000Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 2
  completed_plans: 2
  percent: 50
---

# State: LSR Startup Optimization

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-11)

**Core value:** Reduce lsr startup time by 60%+ (target <200ms) by stripping non-LaTeX modules
**Status:** Phase 1 & 2 complete — Phase 3/4 deferred

## Completed Phases

### Phase 1: Strip Non-LaTeX Modules ✅

- **Commit:** `9bc8e2d5` `feat(phase-01): remove repomap and defer requests loading`
- **Verification:** `5970e945` `docs(phase-01): add verification report`
- **Summary:** `phase-01-01-SUMMARY.md`
- **Changes:**
  - Deleted `lsr/repomap.py` (-867 lines)
  - Deleted `lsr/resources/model-settings.yml` (-338 lines)
  - Deleted `tests/basic/test_repomap.py` (-507 lines)
  - Removed repomap dependency from `base_coder.py`, `models.py`, `openrouter.py`

### Phase 2: Defer Terminal-Only Modules ✅

- **Commit:** `b250ef86` `optimize: defer imports to reduce startup overhead`
- **Summary:** `02-SUMMARY.md`
- **Changes:**
  - Delayed `prompt_toolkit` import into local scope
  - Delayed `Commands` / `SwitchCoder` import into local scope
  - Removed module-level dynamic `edit_format_choices` gathering from `args.py`
  - Added `--version` fast-path in `__main__.py`

## Deferred Phases

### Phase 3: Optimize Core Initialization ⏸️

- **Status:** Discuss-phase complete — context gathered, decisions locked
- **Context:** `03-CONTEXT.md`
- **Deferred decisions (D-01 ~ D-09):**
  - `model_info_manager` lazy singleton
  - Cache directory deferred creation
  - `get_parser()` single invocation
  - `litellm.validate_environment()` moved to sanity-check path
- **Reason for deferral:** Core optimizations achieved in Phase 1 & 2; remaining items are micro-optimizations

### Phase 4: Validation & Benchmarking ⏸️

- **Status:** Not started
- **Reason for deferral:** No dedicated benchmark harness created; user accepts manual verification

## Metrics

| Metric | Before | Target | After Phase 1+2 | Status |
|--------|--------|--------|-----------------|--------|
| Total startup | 590ms | <200ms | ~330ms (estimated) | Partially met |
| `requests` chain | 146ms | 0ms | 0ms | ✅ |
| `tree_sitter` chain | 18ms | 0ms | 0ms | ✅ |
| `lsr.coders` chain | 200ms | 0ms | ~100ms | ⚠️ Partial |
| `prompt_toolkit` | 69ms | 0ms | 0ms | ✅ |
| `lsr.commands` | 143ms | 0ms | 0ms | ✅ |

## Blockers

None

---
*State updated: 2026-06-12 — Phase 1 & 2 complete, Phase 3/4 deferred*
