# Issue 01 — Build the runtime profiling harness

**Status:** ready-for-human
**Parent:** `.scratch/runtime-perf/PRD.md`

## What to build

A reusable profiling script (`scripts/profile_runtime.py`) that profiles lsr's major
runtime operations and emits a hotspot report. It must cover compilation, LSP startup,
section parsing, the chat-completion send path, and startup. It must **separate
lsr-internal time from external waits** (compiler subprocess, LLM API round-trip).
It must degrade gracefully — clear skip-and-report when an operation's prerequisites
are missing (no compiler binary, no LSP server, no API key). A startup-only fast mode
satisfies the deferred Phase-4 startup benchmark and runs without a document or API
key.

The harness uses stdlib profiling primitives (`cProfile` for CPU attribution on lsr
code, `time.perf_counter` for operation boundaries) — no new profiling dependency.

## Acceptance criteria

- [x] One script runs profiles for: compile, LSP startup, section parsing, the chat
      send path, and startup; each profile is independently selectable.
- [x] A startup-only fast mode runs without a document or API key, delivering the
      Phase-4 startup benchmark that was never built.
- [x] For compile and chat, lsr-internal time is measured separately from external
      subprocess/API wait; the report never mixes them in a single number.
- [x] Missing prerequisites cause a clear skip-and-report for that profile, not a
      crash of the whole run.
- [x] The script emits a human-readable hotspot report.
- [x] The decision logic (which profiles run, how internal vs. external time is
      classified, how missing prerequisites are skipped) is unit-tested — not the
      timing numbers themselves.
- [x] Full `pytest` suite stays green.

## Blocked by

None — can start immediately.
