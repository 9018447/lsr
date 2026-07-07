# Issue 04 — Reduce chat first-call overhead

**Status:** done
**Parent:** `.scratch/runtime-perf/PRD.md`

## What to build

The baseline (`02-baseline-hotspot-report`) identified `chat` as the #2 lsr-internal
hotspot at 0.1438s internal (74.2% internal — the rest is the LLM API round-trip,
which is external and out of scope). The internal portion is first-call litellm/model
initialization. Reduce chat-path internal time by ≥30% (target ≤0.10s) by deferring
that overhead: keep the litellm import lazy, avoid eager model-cost-map fetching, and
defer model-metadata loading until the first completion is actually sent.

## Acceptance criteria

- [x] Chat-path internal time, measured by the harness `chat` profile, drops ≥30% from
      the 0.1438s baseline (target ≤0.10s). **0.0806s** (-44%); already met via B3's
      Model-construction deferrals. Note: the harness pre-imports `lsr.models`/`litellm`
      outside its timed window, so this metric understates real first-call cost.
- [x] No eager litellm import or model-cost-map fetch at startup or first
      `Model(...)` construction. litellm stays lazy (`LazyLiteLLM`); **B4 deferred the
      `lsr.openrouter` → `requests` import chain** (moved `import requests` inside
      `OpenRouterModelManager._update_cache`, the sole caller). `lsr.models` import:
      **94.8ms → 48.8ms** (-46ms); `lsr.openrouter` import: 58.7ms → 1.1ms.
- [x] Model metadata is loaded lazily, only when first needed (`_LazyModelInfoManager`
      from B3; `Model.info` is a lazy property).
- [x] The first real chat completion's request shape is unchanged (behavior-preserving;
      `OpenRouterModelManager` still functional).
- [x] Full `pytest` suite green (435 passed); black 23.3.0 + flake8 clean.

## Blocked by

- `01-build-profiling-harness` — needs the harness to measure.
- `02-baseline-hotspot-report` — source of the 0.1438s target.
