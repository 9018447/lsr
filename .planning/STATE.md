---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-06-11T13:49:46.289Z"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 1
  completed_plans: 0
  percent: 0
---

# State: LSR Startup Optimization

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-11)

**Core value:** Reduce lsr startup time by 60%+ (target <200ms) by stripping non-LaTeX modules
**Current focus:** Phase 1 — Strip Non-LaTeX Modules

## Current Phase

**Phase 1: Strip Non-LaTeX Modules**

- **Goal:** Remove or aggressively lazy-load modules irrelevant to LaTeX writing
- **Requirements:** STRIP-01 (repomap), STRIP-02 (openrouter/requests)
- **Status:** Ready to execute
- **Context:** `.planning/phases/phase-01/1-CONTEXT.md`

## Completed Work

- ✓ Quantitative import-time analysis (`python -X importtime`)
- ✓ Identified 590ms total startup, top bottlenecks mapped
- ✓ GSD planning documents created and updated with user constraints
- ✓ Discuss-phase completed — key decisions locked:
  - Repomap is unnecessary for LaTeX (D1)
  - OpenRouter must not be default-loaded (D2)
  - Git support retained (D3)

## Blockers

None

## Next Actions

1. [ ] Move `requests` import inside `OpenRouterModelManager` methods (`openrouter.py`)
2. [ ] Defer `OpenRouterModelManager` instantiation in `ModelInfoManager` (`models.py`)
3. [ ] Guard `lsr.repomap` import behind `use_repo_map` flag (`base_coder.py`)
4. [ ] Run benchmark to verify ~164ms improvement

## Metrics

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Total startup | 590ms | <200ms | 590ms |
| `requests` chain | 146ms | 0ms | 146ms |
| `tree_sitter` chain | 18ms | 0ms | 18ms |
| `lsr.coders` chain | 200ms | 0ms | 200ms |
| `prompt_toolkit` | 69ms | 0ms | 69ms |
| `lsr.commands` | 143ms | 0ms | 143ms |

---
*State updated: 2026-06-11 after discuss-phase context update*
