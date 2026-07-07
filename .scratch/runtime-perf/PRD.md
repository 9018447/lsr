# PRD: Runtime Performance Profiling & Optimization

**Status:** ready-for-agent
**Created:** 2026-07-07
**Slug:** `runtime-perf`

## Problem Statement

`lsr` has already shipped startup optimizations (Phases 1-2 took cold start from
~590 ms to ~330 ms), but **runtime performance is unmeasured**. When a researcher
runs a compile, parses document sections, warms the LSP, or sits in the chat loop,
no one knows where lsr's *own* time goes — versus time it cannot control (the
`pdflatex`/`xelatex`/`lualatex` subprocess, the LLM API round-trip).

The deferred Phase 4 of the startup project called for a benchmark script that was
never built. Without a repeatable profiling harness, any runtime optimization is a
guess: you cannot confirm a hotspot improved, and you cannot guard against
regressions. The risk is optimizing things that don't matter (external waits) while
the real lsr-internal overhead stays hidden.

## Solution

A reusable profiling harness plus a targeted optimization pass, in two phases:

1. **Build the harness.** A repo script that profiles the major runtime operations —
   compilation, LSP startup, section parsing, the chat-completion send path, and
   (folding in the deferred Phase 4) startup — and emits a hotspot report that
   **separates lsr-internal CPU/time from external waits** (compiler subprocess,
   LLM API). This subsumes the never-built startup benchmark.
2. **Profile, then optimize the top-K.** Run the harness to produce a baseline,
   identify the top 2-3 *lsr-internal* hotspots, and implement optimizations that
   each cut a hotspot's measured time by ≥30% — with zero behavioral regression.

Profiling is the means, measurable speedup is the goal. Because the optimization
targets are only knowable after profiling, the optimization issues are written
post-baseline rather than guessed up front.

## User Stories

1. As a maintainer, I want to run one script and get a report of where lsr spends time
   across compile, LSP startup, section parsing, the chat send path, and startup.
2. As a maintainer, I want the report to separate time lsr can control (its own code)
   from time it cannot (the compiler subprocess, the LLM API round-trip), so I do not
   optimize things that are externally bounded.
3. As a maintainer, I want the harness to be repeatable, so I can run before/after and
   prove an optimization actually moved the number.
4. As a maintainer, I want the baseline report checked in under the planning directory,
   so the starting point is auditable.
5. As a maintainer, I want the top-K internal hotspots identified and ranked, so
   optimization effort goes where it matters.
6. As a researcher, I want lsr's own overhead reduced after the top hotspots are
   optimized, so interactive editing and compilation feel snappier.
7. As a researcher, I want startup to stay at or below its current ~330 ms (and
   continue toward the original <200 ms target) — never regress.
8. As a maintainer, I want the startup benchmark that Phase 4 never delivered to
   finally exist as part of this harness.
9. As a maintainer, I want each optimization to be verifiable in isolation against the
   harness numbers, not hand-waved.
10. As a maintainer, I want the full pytest suite to stay green and the compiled
    document output to be byte-identical, so performance work cannot quietly change
    behavior.
11. As a maintainer, I want the profiling harness to degrade gracefully (clear skip /
    warning) when an optional operation is unavailable (no `pdflatex` on PATH, no LSP
    server, no API key), rather than failing the whole run.
12. As a maintainer, I want the harness to support a "startup-only" fast mode, so it
    can run in CI or a tight edit loop without needing a full document + API key.
13. As a researcher, I want all performance improvements to be behavior-preserving —
    the same edits, the same compiled PDF.

## Implementation Decisions

- **One reusable script, multiple operation profiles.** The harness covers compile,
  LSP startup, section parsing, chat send, and startup; each can be enabled
  independently. A startup-only fast mode satisfies the Phase-4 benchmark goal and CI.
- **Internal-vs-external separation is a first-class requirement.** For compile and
  chat, the harness measures lsr-side work separately from subprocess/API wait
  (e.g. timing around `litellm.completion` vs. the call itself; `subprocess.run`
  wall-time vs. lsr's pre/post processing). Reports that mix these are rejected.
- **Baseline artifact checked into the planning directory**, recording the measured
  hotspots and their numbers, so the optimization issues can cite concrete targets.
- **Optimization issues are written post-baseline.** Because targets are only known
  after profiling, the issue list for phase 2 is filled in from the baseline report,
  not pre-committed. Expect ~2-3 optimization issues.
- **Behavior preservation is non-negotiable.** Every optimization must keep the full
  pytest suite green and produce a byte-identical compiled document. If an
  optimization would change output, it is rejected.
- **External waits are explicitly out of scope** for optimization — `pdflatex`/LSP
  subprocess time and LLM API latency are not controllable by lsr and will not be
  "optimized" (only measured).
- **`base_coder.py` is not refactored** as a goal of this PRD. It is large and a known
  maintenance burden, but it is only touched if and where profiling identifies it as a
  top internal hotspot; a standalone refactor is a separate effort.
- **Deferred Phase 3 micro-optimizations** (lazy `model_info_manager` singleton,
  deferred cache-dir creation, single `get_parser` invocation, deferred
  `validate_environment`) remain deferred unless the harness flags one of them as a
  top hotspot, in which case the relevant item is pulled in as an optimization issue.
- **The harness uses stdlib profiling primitives** (`cProfile` for CPU attribution on
  lsr code, `time.perf_counter` for operation boundaries) — no new profiling
  dependency.

## Testing Decisions

- **Performance is not unit-testable; the harness is the verification artifact.**
  Each optimization is verified by a before/after run of the harness showing the
  hotspot dropped ≥30%, plus the full pytest suite green and the compiled document
  byte-identical.
- **Byte-identical compile check:** for any optimization touching the compile path,
  the compiled output (PDF / log) before and after must match; this is the guard
  against silent behavior change.
- **Graceful degradation is tested:** the harness must skip-and-report (not crash)
  when an operation's prerequisites are missing (no compiler binary, no LSP server,
  no API key). This is the one true unit-testable behavior of the harness.
- **Prior art:** `tests/test_latex_tools.py` (compiler-invocation logic) and the
  existing startup fast-path in `__main__.py` are the closest patterns; the harness's
  own logic follows the same "pure logic in testable functions, IO at the edges"
  shape.
- **What makes a good test here:** assert the harness's *decision logic* (which
  operations to run, how it classifies internal vs. external time, how it skips on
  missing prerequisites) — not specific timing numbers, which are
  machine-dependent.

## Out of Scope

- **External-wait optimization** — compiler subprocess time and LLM API latency are
  measured only, never "optimized."
- **`base_coder.py` standalone refactor** — unless profiling identifies it as a top
  hotspot.
- **Deferred Phase 3 micro-optimizations** — unless profiling flags one.
- **Any change that alters compiled output or editing behavior** — performance work
  is strictly behavior-preserving.
- **A remote/cloud benchmark service** — everything runs locally.

## Further Notes

- This PRD closes the gap left by the deferred Phase 4 benchmark; the startup
  benchmark becomes the "startup-only fast mode" of the new harness.
- The dependency structure is strict: harness → baseline report → optimization
  issues. Do not start an optimization issue before its hotspot is confirmed by the
  baseline.
- Success is measured against the baseline this PRD itself produces; the ≥30%-per-
  hotspot target is the bar, not a pre-existing industry number.
