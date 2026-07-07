# Issue 02 — Baseline hotspot report

**Status:** ready-for-human
**Parent:** `.scratch/runtime-perf/PRD.md`

## What to build

Run the profiling harness from issue 01 to produce a baseline report that identifies
and ranks the top 2-3 **lsr-internal** hotspots (excluding external waits). Check the
report into the planning directory so the starting point is auditable. The report
names the concrete optimization targets that the (deferred) optimization issues B3+
will be created from, and flags any deferred Phase-3 micro-optimization item or
`base_coder.py` region that surfaces as a top hotspot.

This report is the data-driven input for the follow-on optimization work.

## Acceptance criteria

- [x] A baseline report is checked into `.planning/` recording the measured hotspots
      and their numbers.
- [x] The report ranks the top 2-3 lsr-internal hotspots; external waits (compiler
      subprocess, LLM API) are explicitly excluded from the optimization target list.
- [x] The report identifies the 2-3 concrete optimization targets that follow-on
      optimization issues will address.
- [x] Any deferred Phase-3 item (lazy `model_info_manager` singleton, deferred
      cache-dir creation, single `get_parser`, deferred `validate_environment`) or
      `base_coder.py` region flagged as a top hotspot is called out explicitly.
- [x] The report records the selection reasoning so the optimization targets are
      auditable later.

## Blocked by

- `01-build-profiling-harness` — requires the profiling harness to exist.
