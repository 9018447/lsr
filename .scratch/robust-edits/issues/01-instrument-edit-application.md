# Issue 01 — Instrument edit-application with fallback tagging

**Status:** ready-for-human
**Parent:** `.scratch/robust-edits/PRD.md`

## What to build

Add lightweight structured observability to the edit-application pipeline so that
every edit attempt is recorded: whether it applied or failed, *which* fuzzy-matching
fallback handled it, the document type, and the model. Write one JSONL line per edit
attempt to a file under the lsr state directory. The matcher chain gains a single
return channel that tags which strategy succeeded. The log sink must be crash-safe:
a write failure never propagates into the edit path.

This is the foundation for data-driven hardening — without it, "robustness" cannot be
measured or improved with confidence.

## Acceptance criteria

- [x] Every edit attempt emits exactly one JSONL line to a file under the lsr state
      directory, with fields: timestamp, file basename (not absolute path), document
      type, model name, outcome (`applied` / `failed`), and `fallback` tag.
- [x] The `fallback` tag is drawn from a fixed enum covering the existing chain:
      `perfect`, `whitespace`, `unicode`, `latex-escape`, `ignore-linebreaks`,
      `prefix`, `missing-whitespace`, `edit-distance`, `similar-lines`, and the
      ANCHOR/REPLACE `anchor-headtail` path. `failed` edits tag the last strategy
      attempted.
- [x] The matcher chain records/returns which strategy handled each successful match
      (this tag is both logged and assertable in tests).
- [x] A log-write failure (read-only directory, missing directory, disk full) is
      caught and logged to the existing `io` warning channel; it never raises into the
      edit-application path.
- [x] No prompt files are modified (`main_system`, `system_reminder`, the
      example-message set in the diff coder prompts must be untouched).
- [x] `tests/test_edit_observability.py` asserts: required fields present, correct
      fallback tag on known input shapes, and crash-safety when the log path is
      unwritable.
- [x] Full `pytest` suite stays green.

## Blocked by

None — can start immediately.
