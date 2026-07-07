# Issue 03 — Harden ANCHOR/REPLACE head/tail matching

**Status:** done
**Parent:** `.scratch/robust-edits/PRD.md`

## What to build

The failure-distribution baseline (`02-failure-distribution-baseline`) showed that
**ANCHOR/REPLACE is the only domain with hard failures**: 2 of 6 cases (33.3%) fail,
both routed through the `anchor-headtail` matcher. The two named failure modes are:

- `tail_whitespace_drift` — the anchor's tail has different trailing whitespace than
  the file content, so the head/tail span cannot be located.
- `missing_tail_anchor` — the LLM omits the tail anchor entirely.

Make the ANCHOR/REPLACE head/tail matcher fuzzier so these recover: tolerate
whitespace drift in the head/tail anchors, and handle a missing/empty tail anchor by
falling back to a sentence/paragraph-boundary heuristic. Typst and Markdown are
**out of scope** for this issue — the baseline recorded zero hard failures there.

Measure before/after on the same corpus used by issue 02.

## Acceptance criteria

- [x] The two named failure modes (`tail_whitespace_drift`, `missing_tail_anchor`)
      from the baseline now apply correctly on the issue-02 corpus.
- [x] Anchor-domain failure rate drops from 33.3% (2/6) to 0% — a 100% reduction
      (≥50%), measured by re-running `.scratch/robust-edits/run_failure_distribution.py`.
- [x] No regression in currently-passing matching: full `pytest` green (435 passed),
      including `tests/test_anchor_replace.py` and `tests/test_latex_matching.py`.
- [x] New regression cases added (covering both fixed modes, plus an ordering-error
      guard) following the existing `tests/test_anchor_replace.py` pattern; distinct
      tag assertions added in `tests/test_edit_observability.py`.
- [x] The new anchor handling records distinct fallback tags (`anchor-tail-whitespace`,
      `anchor-missing-tail`) via the issue-01 observability, so each path stays
      individually measurable.
- [x] No prompt files modified (`main_system`, `system_reminder`, example messages).

## Blocked by

- `02-failure-distribution-baseline` — needs the instrumented corpus and baseline
  numbers to measure the reduction against.
