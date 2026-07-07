# Failure-Distribution Baseline Report

**Project:** robust-edits

**Source:** `.scratch/robust-edits/run_failure_distribution.py`

**Purpose:** With the instrumentation from issue 01 in place, this report records the failure distribution of a typed synthetic corpus so that follow-on hardening issues can target verified failure modes.

## Summary

| Domain | Cases | Failures | Failure Rate |
|--------|-------|----------|-------------|
| typst | 8 | 0 | 0.0% |
| markdown | 9 | 0 | 0.0% |
| anchor | 6 | 0 | 0.0% |

## Per-Domain Failure Breakdown

### typst


No hard failures recorded.


Applied edits that required a non-perfect fallback:

| Fallback | Count |
|----------|-------|
| edit-distance | 2 |
| ignore-linebreaks | 1 |

Failed cases:

- None

### markdown


No hard failures recorded.


Applied edits that required a non-perfect fallback:

| Fallback | Count |
|----------|-------|
| edit-distance | 3 |

Failed cases:

- None

### anchor


No hard failures recorded.


Applied edits that required a non-perfect fallback:

| Fallback | Count |
|----------|-------|
| anchor-headtail | 4 |
| anchor-tail-whitespace | 1 |
| anchor-missing-tail | 1 |

Failed cases:

- None

## Top-K Failure Modes and Hardening Targets

The selection below ranks concrete failure modes by count and by the observed fallback tag.  Both hard failures and applied edits that required a non-perfect fallback are considered, because the latter show where the current matcher is being stressed.  The reasoning is recorded so the choice is auditable.

| Rank | Domain | Fallback | Count | Selection Rationale |
|------|--------|----------|-------|---------------------|
| 1 | anchor | anchor-headtail | 4 | ANCHOR/REPLACE blocks fail or stress the head/tail matcher; fuzzier anchor matching (whitespace/mid-sentence drift) is needed. |
| 2 | markdown | edit-distance | 3 | Markdown SEARCH blocks fall back to edit-distance; fence collisions and heading/hash-marker normalization are the likely drivers. |
| 3 | typst | edit-distance | 2 | Typst SEARCH blocks fall back to edit-distance; document-type awareness for headings/comment markers should recover these. |
| 4 | typst | ignore-linebreaks | 1 | Typst SEARCH blocks require line-break folding; document-type awareness should keep this fallback but make it more predictable. |
| 5 | anchor | anchor-tail-whitespace | 1 | Observed stressful fallback; harden if data volume grows. |
| 6 | anchor | anchor-missing-tail | 1 | Observed stressful fallback; harden if data volume grows. |

### Selected Hardening Targets (2–4 modes)

1. **anchor / anchor-headtail** — 4 case(s). ANCHOR/REPLACE blocks fail or stress the head/tail matcher; fuzzier anchor matching (whitespace/mid-sentence drift) is needed.

2. **markdown / edit-distance** — 3 case(s). Markdown SEARCH blocks fall back to edit-distance; fence collisions and heading/hash-marker normalization are the likely drivers.

3. **typst / edit-distance** — 2 case(s). Typst SEARCH blocks fall back to edit-distance; document-type awareness for headings/comment markers should recover these.

4. **typst / ignore-linebreaks** — 1 case(s). Typst SEARCH blocks require line-break folding; document-type awareness should keep this fallback but make it more predictable.

## Raw JSONL Records

```jsonl
{"timestamp": "2026-07-07T11:21:50.666892+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.666978+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667028+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667068+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667360+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "edit-distance"}
{"timestamp": "2026-07-07T11:21:50.667462+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "ignore-linebreaks"}
{"timestamp": "2026-07-07T11:21:50.667533+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667696+00:00", "basename": "main.typ", "document_type": "typst", "model": "baseline-synthetic", "outcome": "applied", "fallback": "edit-distance"}
{"timestamp": "2026-07-07T11:21:50.667760+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667802+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667839+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.667981+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "edit-distance"}
{"timestamp": "2026-07-07T11:21:50.668026+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.668063+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.668097+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "perfect"}
{"timestamp": "2026-07-07T11:21:50.668182+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "edit-distance"}
{"timestamp": "2026-07-07T11:21:50.668340+00:00", "basename": "main.md", "document_type": "markdown", "model": "baseline-synthetic", "outcome": "applied", "fallback": "edit-distance"}
{"timestamp": "2026-07-07T11:21:50.668371+00:00", "basename": "main.tex", "document_type": "latex", "model": "baseline-synthetic", "outcome": "applied", "fallback": "anchor-headtail"}
{"timestamp": "2026-07-07T11:21:50.668399+00:00", "basename": "main.tex", "document_type": "latex", "model": "baseline-synthetic", "outcome": "applied", "fallback": "anchor-headtail"}
{"timestamp": "2026-07-07T11:21:50.668425+00:00", "basename": "main.tex", "document_type": "latex", "model": "baseline-synthetic", "outcome": "applied", "fallback": "anchor-tail-whitespace"}
{"timestamp": "2026-07-07T11:21:50.668448+00:00", "basename": "main.tex", "document_type": "latex", "model": "baseline-synthetic", "outcome": "applied", "fallback": "anchor-headtail"}
{"timestamp": "2026-07-07T11:21:50.668471+00:00", "basename": "main.tex", "document_type": "latex", "model": "baseline-synthetic", "outcome": "applied", "fallback": "anchor-headtail"}
{"timestamp": "2026-07-07T11:21:50.668501+00:00", "basename": "main.tex", "document_type": "latex", "model": "baseline-synthetic", "outcome": "applied", "fallback": "anchor-missing-tail"}
```

## Selection Reasoning

The ranking above is produced from a synthetic corpus that mirrors the malformed-but-realistic LLM outputs described in the PRD.  The top modes concentrate in the two document-type domains (Typst and Markdown) and in the ANCHOR/REPLACE head/tail path.  This matches the PRD hypothesis that the current matcher is LaTeX-centric and that Typst/Markdown/ANCHOR cases need document-type-aware normalization and fuzzier anchor handling.

Follow-on hardening issues (A3+) should address the selected targets in priority order, measuring the before/after failure rate on this same corpus.
