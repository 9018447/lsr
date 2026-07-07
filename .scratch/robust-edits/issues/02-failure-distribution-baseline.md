# Issue 02 — Failure-distribution baseline report

**Status:** ready-for-human
**Parent:** `.scratch/robust-edits/PRD.md`

## What to build

With the edit-application instrumentation from issue 01 in place, build a small
runner that exercises the instrumented matcher over a typed corpus of malformed-but-
realistic LLM outputs (Typst, Markdown, and ANCHOR/REPLACE cases) and aggregates the
JSONL output into a failure-distribution report. The report names the top-K failure
modes within the Typst, Markdown, and ANCHOR/REPLACE domains, with counts, and
records the reasoning for which modes are selected to harden.

This report is the data-driven input that the (deferred) hardening issues A3+ will be
created from.

## Acceptance criteria

- [x] A runnable fixture-runner (script or test-adjacent harness) feeds typed
      malformed SEARCH/REPLACE and ANCHOR/REPLACE inputs to the matcher and aggregates
      the resulting JSONL into a per-domain distribution.
- [x] The corpus covers Typst (`==`/`===` headings, `//` comments, Typst escapes),
      Markdown (`#` headings, `<!-- -->` markers, fence collisions), and ANCHOR/
      REPLACE long-paragraph head/tail drift.
- [x] A report is written under `.scratch/robust-edits/` naming the top-K failure
      modes per domain, with counts and the dominant fallback invoked.
- [x] The report explicitly identifies the 2-4 hardening targets (concrete failure
      modes) that the follow-on hardening issues will address.
- [x] The report records the selection reasoning so the choice is auditable later.
- [x] No prompt files are modified.

## Blocked by

- `01-instrument-edit-application` — requires the JSONL instrumentation to exist.
