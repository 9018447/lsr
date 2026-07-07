# Issue 03 — Startup optimization (Phase-3 resurrection)

**Status:** done
**Parent:** `.scratch/runtime-perf/PRD.md`

## What to build

The baseline (`02-baseline-hotspot-report`) identified `startup` as the #1 lsr-internal
hotspot at 0.2316s (100% internal). This is exactly the deferred Phase-3
micro-optimization list from `.planning/`. Reduce startup internal time by ≥30%
(target ≤0.16s) by resurrecting those items: call `get_parser()` exactly once per
`main()` invocation, make `model_info_manager` a lazy singleton, defer cache-directory
creation, and defer `litellm.validate_environment()` until first actual model use.

## Acceptance criteria

- [x] Startup internal time, measured by `scripts/profile_runtime.py --startup-only`,
      drops ≥30% from the 0.2316s baseline (target ≤0.16s). Before/after numbers
      recorded.
      - Baseline: 0.2316s
      - After: ~0.066s (median of three runs: 0.0665s, 0.0657s, 0.0691s)
      - Improvement: ~71%
- [x] `get_parser()` is called exactly once per `main()` invocation.
- [x] `Model(...)` construction does not trigger `litellm.validate_environment()` or
      create the cache directory until the first actual model use.
- [x] `model_info_manager` is created lazily (not at import time).
- [x] The `lsr --version` / `--help` fast paths remain fast (no new imports on those
      paths). `--version` stays ~0.033s.
- [x] Full `pytest` suite green (430 passed).

## Blocked by

- `01-build-profiling-harness` — needs the harness to measure.
- `02-baseline-hotspot-report` — source of the 0.2316s target.
