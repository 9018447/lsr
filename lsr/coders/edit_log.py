"""Structured observability logging for the edit-application pipeline."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lsr.document_types import get_document_type


# Fixed enum of fallback tags.  New hardening issues may add values, but
# existing values must remain stable so JSONL aggregations stay valid.
class FallbackTag:
    PERFECT = "perfect"
    WHITESPACE = "whitespace"
    UNICODE = "unicode"
    LATEX_ESCAPE = "latex-escape"
    IGNORE_LINEBREAKS = "ignore-linebreaks"
    PREFIX = "prefix"
    MISSING_WHITESPACE = "missing-whitespace"
    EDIT_DISTANCE = "edit-distance"
    SIMILAR_LINES = "similar-lines"
    ANCHOR_HEADTAIL = "anchor-headtail"
    ANCHOR_TAIL_WHITESPACE = "anchor-tail-whitespace"
    ANCHOR_MISSING_TAIL = "anchor-missing-tail"


VALID_TAGS = frozenset(
    {
        FallbackTag.PERFECT,
        FallbackTag.WHITESPACE,
        FallbackTag.UNICODE,
        FallbackTag.LATEX_ESCAPE,
        FallbackTag.IGNORE_LINEBREAKS,
        FallbackTag.PREFIX,
        FallbackTag.MISSING_WHITESPACE,
        FallbackTag.EDIT_DISTANCE,
        FallbackTag.SIMILAR_LINES,
        FallbackTag.ANCHOR_HEADTAIL,
        FallbackTag.ANCHOR_TAIL_WHITESPACE,
        FallbackTag.ANCHOR_MISSING_TAIL,
    }
)


DEFAULT_LOG_PATH = Path.home() / ".lsr" / "edit_log.jsonl"


class EditLog:
    """Crash-safe JSONL sink for edit-application events.

    Write failures are caught and reported via the IO warning channel; they
    never propagate into the edit path.
    """

    def __init__(self, io=None, path=None):
        self.io = io
        self.path = Path(path) if path else DEFAULT_LOG_PATH

    def log(self, fname, model, outcome, fallback):
        """Append a single JSONL record describing one edit attempt.

        Args:
            fname: Path-like object for the file being edited.
            model: Model name string.
            outcome: "applied" or "failed".
            fallback: A value from FallbackTag.
        """
        try:
            if fallback not in VALID_TAGS:
                fallback = FallbackTag.EDIT_DISTANCE

            doc_type = get_document_type(str(fname))
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "basename": Path(fname).name,
                "document_type": doc_type.name if doc_type else "unknown",
                "model": model or "unknown",
                "outcome": outcome,
                "fallback": fallback,
            }

            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            if self.io:
                self.io.tool_warning(f"Could not write edit log: {e}")


def edit_log_path():
    """Return the effective edit-log path (overridable for tests)."""
    return Path(os.environ.get("LSR_EDIT_LOG_PATH", DEFAULT_LOG_PATH))
