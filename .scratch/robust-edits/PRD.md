# PRD: Robust Edits — Edit-Application Pipeline Robustness

**Status:** ready-for-agent
**Created:** 2026-07-07
**Slug:** `robust-edits`

## Problem Statement

When `lsr` asks the LLM to edit a LaTeX, Typst, or Markdown manuscript, the model
returns edits in a SEARCH/REPLACE (or ANCHOR/REPLACE) block. The edit-application
pipeline must locate the SEARCH text inside the file and replace it. In practice
the model's output is messy: Unicode math symbols get rendered as ASCII lookalikes,
LaTeX escapes are dropped, long lines are re-wrapped, leading whitespace is lost,
filenames are misspelled, and ANCHOR/REPLACE head/tail anchors drift on long
paragraphs.

`lsr` already defends against many of these with a stack of fuzzy-matching fallbacks
in the diff coder. But that defense is **LaTeX-centric and unmeasured**:

- There is **no observability**: nothing records *which* fallback handled each edit,
  how often matching fails, or which document types and models fail most. "Robustness"
  is therefore unfalsifiable — no one can tell whether a change helped.
- The fallbacks were tuned for `.tex`. **Typst** (`==`/`===` headings, `//` comments,
  different escape rules) and **Markdown** (`#` headings, `<!-- -->` hash markers,
  code-block fence collisions) have no document-type-aware handling.
- **ANCHOR/REPLACE** fuzzy head/tail matching has known edge cases on long paragraphs
  that still slip through.

The result: edits silently fail to match, the model is asked to retry, and the
researcher experiences flaky, slow editing — with no way to diagnose it.

## Solution

A **data-driven hardening** of the edit-application pipeline, in three steps:

1. **Instrument first.** Add lightweight structured logging to the edit-application
   path that records, per edit: which fallback in the matching chain actually handled
   it (perfect / whitespace / unicode-normalized / edit-distance / prefix / missing-
   whitespace / similar-lines / ANCHOR head-tail), whether it failed, the document
   type, and the model. Output to a JSONL file under the lsr state directory.
2. **Read the data.** Collect a failure distribution from real editing sessions (and
   a synthetic corpus in tests) to identify the top failure modes within the Typst,
   Markdown, and ANCHOR/REPLACE domains.
3. **Harden what the data shows.** Add document-type-aware normalization and matching
   for the confirmed top failure modes; lower the silent-failure rate by ≥50% on the
   top modes.

The prompt side (rewriting `main_system` / `system_reminder` / the few-shot example
set) is **explicitly deferred** to a separate future effort; this PRD touches only
the parser/matcher and the observability layer.

## User Stories

1. As a researcher editing a Typst manuscript, when the LLM emits a SEARCH block
   containing Typst `==`/`===` headings, I want lsr to apply it without a failed-
   match retry, so that editing feels reliable.
2. As a researcher editing a Typst manuscript, when the LLM uses Typst `//` line
   comments or Typst-specific escape sequences in a SEARCH block, I want the matcher
   to normalize them correctly.
3. As a researcher editing a Markdown file, when the LLM emits a SEARCH block around
   `#`/`##` headings or `<!-- === ... === -->` hash markers, I want lsr to match it
   even when the comment syntax is slightly off.
4. As a researcher editing a Markdown file, when the SEARCH block spans a fenced code
   region whose fence collides with the edit-block fence, I want lsr to recover rather
   than fail.
5. As a researcher using ANCHOR/REPLACE on a long paragraph, when the head or tail
   anchor drifts by a few words, I want lsr to still locate the correct span and apply
   the replacement.
6. As a researcher, when an edit genuinely cannot match, I want the retry feedback to
   the model to carry enough structure that the retry is likely to succeed.
7. As a maintainer, I want every applied edit to be logged with *which* fallback
   handled it, so I can see where the pipeline is being stressed.
8. As a maintainer, I want the parse-failure count and rate logged, broken down by
   document type (latex/typst/markdown) and by model, so I can prioritize hardening.
9. As a maintainer, I want a JSONL log under the lsr state directory that I can grep
   or aggregate to build a failure-distribution report.
10. As a maintainer, I want a regression test corpus of malformed-but-realistic LLM
    outputs (Typst, Markdown, ANCHOR/REPLACE cases) that asserts the matcher recovers,
    so future changes cannot silently regress robustness.
11. As a maintainer, I want the existing matching thresholds and normalization pipeline
    preserved unless the data shows a specific threshold is mis-tuned, so this work
    does not destabilize currently-working LaTeX matching.
12. As a maintainer, I want the observability logging to be cheap (no perceptible edit
    latency) and safe (never crashes the edit path if the log file is unwritable).
13. As a researcher, I want robustness improvements to be invisible when they work —
    the same editing UX, just fewer "failed to match" retries.
14. As a maintainer, I want the data-driven selection of *which* failure modes to
    harden to be recorded in the issue/summary, so the reasoning is auditable later.

## Implementation Decisions

- **Observability via a JSONL sink.** A single structured log line per edit attempt,
  written to the lsr state directory. Fields: timestamp, file path (basename only, to
  avoid leaking absolute paths), document type, model name, outcome (applied / failed),
  and the fallback that handled it (an enum/tag from a fixed set). Cheapest viable
  observability — no network, no external dependency, stdlib `json`.
- **Fallback tagging.** The existing matching chain (perfect → whitespace → unicode →
  latex-escape → ignore-line-breaks → prefix → missing-whitespace → edit-distance →
  similar-lines, plus the ANCHOR/REPLACE head-tail path) gains a single return channel
  that says *which* strategy succeeded. This is the core instrumentation surface; it is
  also what the tests assert against.
- **Document-type-aware normalization.** Normalization functions that are currently
  LaTeX-shaped (escape handling, fence selection) are generalized to dispatch on the
  document type, with Typst and Markdown branches. Typst: `//` comments, Typst escape
  rules, `=`/`==`/`===` heading awareness. Markdown: `#` headings, `<!-- -->` markers,
  fence-collision handling.
- **ANCHOR/REPLACE edge hardening.** The fuzzy head/tail matcher gains explicit
  handling for the edge cases the data surfaces (e.g. anchor landing mid-sentence,
  whitespace drift in the anchor, anchor shorter than the minimum useful length).
- **No prompt changes.** `main_system`, `system_reminder`, and the example-message set
  are out of scope and must not be edited in this PRD's issues.
- **Data-driven target selection.** The issues that *implement* hardening are written
  only after the observability issue lands and a failure distribution is collected; the
  hardening issues name the top-K modes the data identified. This is a dependency, not
  a guess.
- **Retry-feedback structure** is improved only if the data shows failed retries are a
  top mode; otherwise left alone.
- **Backward compatibility.** The default edit format and all currently-passing LaTeX
  matching behavior must be preserved. Thresholds (edit-distance, similar-lines) are
  not changed unless the data specifically indicts one.

## Testing Decisions

- **Reuse the existing highest seam.** The matcher functions are pure and already
  tested via `tests/test_latex_matching.py`; this PRD extends that corpus rather than
  introducing a new integration seam. New cases are synthetic but realistic malformed
  LLM outputs — no LLM call, no network.
- **New observability test module** asserts the JSONL fields and fallback tags are
  emitted correctly, and that a write failure (read-only / missing directory) never
  propagates into the edit path.
- **What makes a good test here:** assert *external behavior* — given a specific
  malformed SEARCH block and file content, the matcher returns the correctly replaced
  file (and, for observability, the expected fallback tag). Do not assert internal
  call ordering beyond the tag contract.
- **Prior art:** `tests/test_latex_matching.py` (matcher recovery on Unicode / escape /
  whitespace drift) and `tests/test_anchor_replace.py` (ANCHOR/REPLACE head-tail
  matching) are the patterns to follow.
- **No new fixtures framework.** Each new case is a `@pytest.mark.parametrize` row on
  the existing `class Test*` groups, using `tmp_path` where a file is needed.

## Out of Scope

- **Prompt rewriting** (`main_system`, `system_reminder`, the example-message set) —
  deferred to a separate effort.
- **Cross-document-type / multi-file mixed scenarios** (fence conflicts across
  different doc types in one session, wrong-file routing) — not in this PRD.
- **Threshold re-tuning** unless the data specifically indicts a current threshold.
- **Any LLM/network-dependent or integration test** — the suite stays pure-unit.
- **Telemetry/analytics to a remote endpoint** — local JSONL only.

## Further Notes

- The observability log location follows existing lsr conventions for state under the
  user's lsr home directory; the exact filename is an implementation detail settled in
  the first issue.
- This PRD is intentionally data-driven: the *number* and *identity* of hardening
  issues is not fixed up front, because the whole point is to let real failure data
  decide. Expect 1 observability issue + 1 data-collection/summary issue + 2-4
  hardening issues.
- Success is measured against the observability baseline this PRD itself creates;
  there is no pre-existing number to beat.
