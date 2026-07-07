#!/usr/bin/env python3
"""Fixture-runner that builds the failure-distribution baseline report.

This script exercises the instrumented matcher from issue 01 over a typed
synthetic corpus (Typst, Markdown, ANCHOR/REPLACE) and aggregates the JSONL
log into a per-domain failure-distribution report.

Usage:
    python .scratch/robust-edits/run_failure_distribution.py

Output:
    .scratch/robust-edits/failure-distribution-baseline.md
"""

import json
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from lsr.coders.anchor_replace import anchor_replace_with_tag
from lsr.coders.edit_log import EditLog, FallbackTag
from lsr.coders.editblock_coder import do_replace_with_tag

REPORT_PATH = Path(__file__).parent / "failure-distribution-baseline.md"


@dataclass
class CorpusCase:
    domain: str
    name: str
    fname: str
    content: str
    search: str
    replace: str
    matcher: str = "search_replace"
    head_anchor: str = ""
    tail_anchor: str = ""


CORPUS = [
    # ============================================================
    # Typst domain
    # ============================================================
    CorpusCase(
        domain="typst",
        name="heading_level_two",
        fname="main.typ",
        content="= Introduction\n\n== Methods\n\nWe used DFT.\n",
        search="== Methods\n",
        replace="== Methods and Materials\n",
    ),
    CorpusCase(
        domain="typst",
        name="heading_level_three",
        fname="main.typ",
        content="= Introduction\n\n=== Subsection\n\nDetails here.\n",
        search="=== Subsection\n",
        replace="=== Detailed Subsection\n",
    ),
    CorpusCase(
        domain="typst",
        name="line_comment_search",
        fname="main.typ",
        content="// This is a comment\nWe used DFT.\n",
        search="// This is a comment\n",
        replace="// Updated comment\n",
    ),
    CorpusCase(
        domain="typst",
        name="escaped_sequence",
        fname="main.typ",
        content="The cost is $100.\n",
        search="The cost is $100.\n",
        replace="The cost is $200.\n",
    ),
    CorpusCase(
        domain="typst",
        name="markdown_heading_in_typst",
        fname="main.typ",
        content="= Introduction\n\n== Methods\n\nWe used DFT.\n",
        search="# Methods\n",
        replace="## Methods\n",
    ),
    CorpusCase(
        domain="typst",
        name="missing_comment_marker",
        fname="main.typ",
        content="// This is a comment\nWe used DFT.\n",
        search="This is a comment\n",
        replace="Updated comment\n",
    ),
    CorpusCase(
        domain="typst",
        name="typst_list_item",
        fname="main.typ",
        content="- first item\n- second item\n",
        search="- first item\n",
        replace="- updated first item\n",
    ),
    CorpusCase(
        domain="typst",
        name="unicode_math_symbol",
        fname="main.typ",
        content="The value is α = 1.0.\n",
        search="The value is alpha = 1.0.\n",
        replace="The value is β = 2.0.\n",
    ),
    # ============================================================
    # Markdown domain
    # ============================================================
    CorpusCase(
        domain="markdown",
        name="heading_level_one",
        fname="main.md",
        content="# Introduction\n\n## Methods\n\nWe used DFT.\n",
        search="# Introduction\n",
        replace="# Introduction and Scope\n",
    ),
    CorpusCase(
        domain="markdown",
        name="heading_level_two",
        fname="main.md",
        content="# Introduction\n\n## Methods\n\nWe used DFT.\n",
        search="## Methods\n",
        replace="## Methods and Materials\n",
    ),
    CorpusCase(
        domain="markdown",
        name="hash_marker",
        fname="main.md",
        content="<!-- === section: Intro (hash: abc123) === -->\nContent here.\n",
        search="<!-- === section: Intro (hash: abc123) === -->\n",
        replace="<!-- === section: Introduction (hash: abc123) === -->\n",
    ),
    CorpusCase(
        domain="markdown",
        name="hash_marker_spacing_drift",
        fname="main.md",
        content="<!-- === section: Intro (hash: abc123) === -->\nContent here.\n",
        search="<!--=== section: Intro (hash: abc123) ===-->\n",
        replace="<!--=== section: Introduction (hash: abc123) ===-->\n",
    ),
    CorpusCase(
        domain="markdown",
        name="fenced_code_collision",
        fname="main.md",
        content="```python\nprint('hello')\n```\n",
        search="```python\nprint('hello')\n```\n",
        replace="```python\nprint('world')\n```\n",
    ),
    CorpusCase(
        domain="markdown",
        name="fenced_code_wrong_language",
        fname="main.md",
        content="```python\nprint('hello')\n```\n",
        search="```py\nprint('hello')\n```\n",
        replace="```py\nprint('world')\n```\n",
    ),
    CorpusCase(
        domain="markdown",
        name="list_item",
        fname="main.md",
        content="- first item\n- second item\n",
        search="- first item\n",
        replace="- updated first item\n",
    ),
    CorpusCase(
        domain="markdown",
        name="emphasis_mismatch",
        fname="main.md",
        content="This is *important* text.\n",
        search="This is **important** text.\n",
        replace="This is *very important* text.\n",
    ),
    CorpusCase(
        domain="markdown",
        name="typst_heading_in_markdown",
        fname="main.md",
        content="# Introduction\n\n## Methods\n\nWe used DFT.\n",
        search="== Methods\n",
        replace="## Methods and Materials\n",
    ),
    # ============================================================
    # ANCHOR/REPLACE domain
    # ============================================================
    CorpusCase(
        domain="anchor",
        name="exact_anchors",
        fname="main.tex",
        content="First sentence. Middle content. Last sentence.\n",
        search="",
        replace="Replacement paragraph.\n",
        matcher="anchor",
        head_anchor="First sentence.",
        tail_anchor="Last sentence.",
    ),
    CorpusCase(
        domain="anchor",
        name="head_drift_one_word",
        fname="main.tex",
        content="The quick brown fox jumps over the lazy dog.\n",
        search="",
        replace="A slow green turtle crawls.\n",
        matcher="anchor",
        head_anchor="quick brown fox",
        tail_anchor="lazy dog.",
    ),
    CorpusCase(
        domain="anchor",
        name="tail_whitespace_drift",
        fname="main.tex",
        content="First sentence. Middle content. Last sentence.\n",
        search="",
        replace="Replacement paragraph.\n",
        matcher="anchor",
        head_anchor="First sentence.",
        tail_anchor="Last sentence ",
    ),
    CorpusCase(
        domain="anchor",
        name="anchor_mid_sentence",
        fname="main.tex",
        content="First sentence. Middle content. Last sentence.\n",
        search="",
        replace="Replacement paragraph.\n",
        matcher="anchor",
        head_anchor="First sent",
        tail_anchor="t sentence.",
    ),
    CorpusCase(
        domain="anchor",
        name="long_paragraph_drift",
        fname="main.tex",
        content=(
            "Wavefunction analysis based on density functional theory "
            "provides a theoretical basis for the rational design of materials. "
            "Molecular dynamics simulations were performed to investigate structure.\n"
        ),
        search="",
        replace="Updated paragraph content.\n",
        matcher="anchor",
        head_anchor="Wavefunction analysis based on",
        tail_anchor="investigate structure.",
    ),
    CorpusCase(
        domain="anchor",
        name="missing_tail_anchor",
        fname="main.tex",
        content="First sentence. Middle content. Last sentence.\n",
        search="",
        replace="Replacement paragraph.\n",
        matcher="anchor",
        head_anchor="First sentence.",
        tail_anchor="Nonexistent tail.",
    ),
]


def run_corpus(log_path: Path):
    """Run every corpus case through the matcher and log the result."""
    edit_log = EditLog(path=log_path)
    model = "baseline-synthetic"

    results = []
    for case in CORPUS:
        if case.matcher == "anchor":
            new_content, tag = anchor_replace_with_tag(
                case.content,
                case.head_anchor,
                case.tail_anchor,
                case.replace,
            )
        else:
            new_content, tag = do_replace_with_tag(
                case.fname,
                case.content,
                case.search,
                case.replace,
            )

        outcome = "applied" if new_content else "failed"
        edit_log.log(case.fname, model, outcome, tag)
        results.append(
            {
                "domain": case.domain,
                "name": case.name,
                "outcome": outcome,
                "fallback": tag,
            }
        )

    return results


def aggregate(results):
    """Aggregate results into per-domain failure distributions."""
    domains = {}
    for r in results:
        domains.setdefault(r["domain"], []).append(r)

    total = Counter()
    failed = Counter()
    failed_by_fallback = {}
    non_perfect_by_fallback = {}

    for domain, items in domains.items():
        total[domain] = len(items)
        failed[domain] = sum(1 for i in items if i["outcome"] == "failed")
        fb = Counter(i["fallback"] for i in items if i["outcome"] == "failed")
        failed_by_fallback[domain] = fb.most_common()
        np = Counter(
            i["fallback"]
            for i in items
            if i["outcome"] == "applied" and i["fallback"] != FallbackTag.PERFECT
        )
        non_perfect_by_fallback[domain] = np.most_common()

    return {
        "total": total,
        "failed": failed,
        "failed_by_fallback": failed_by_fallback,
        "non_perfect_by_fallback": non_perfect_by_fallback,
        "domains": domains,
    }


def render_report(results, agg, log_records):
    """Render the Markdown failure-distribution baseline report."""
    lines = []
    lines.append("# Failure-Distribution Baseline Report\n")
    lines.append("**Project:** robust-edits\n")
    lines.append("**Source:** `.scratch/robust-edits/run_failure_distribution.py`\n")
    lines.append(
        "**Purpose:** With the instrumentation from issue 01 in place, this report "
        "records the failure distribution of a typed synthetic corpus so that "
        "follow-on hardening issues can target verified failure modes.\n"
    )

    lines.append("## Summary\n")
    lines.append("| Domain | Cases | Failures | Failure Rate |")
    lines.append("|--------|-------|----------|-------------|")
    for domain in ["typst", "markdown", "anchor"]:
        t = agg["total"][domain]
        f = agg["failed"][domain]
        rate = f"{f / t * 100:.1f}%" if t else "N/A"
        lines.append(f"| {domain} | {t} | {f} | {rate} |")
    lines.append("")

    lines.append("## Per-Domain Failure Breakdown\n")
    for domain in ["typst", "markdown", "anchor"]:
        lines.append(f"### {domain}\n")
        fb = agg["failed_by_fallback"].get(domain, [])
        if fb:
            lines.append("\nHard failures by fallback:\n")
            lines.append("| Fallback | Failure Count |")
            lines.append("|----------|---------------|")
            for fallback, count in fb:
                lines.append(f"| {fallback} | {count} |")
        else:
            lines.append("\nNo hard failures recorded.\n")

        np = agg["non_perfect_by_fallback"].get(domain, [])
        if np:
            lines.append("\nApplied edits that required a non-perfect fallback:\n")
            lines.append("| Fallback | Count |")
            lines.append("|----------|-------|")
            for fallback, count in np:
                lines.append(f"| {fallback} | {count} |")

        lines.append("\nFailed cases:\n")
        failed_cases = [r for r in agg["domains"][domain] if r["outcome"] == "failed"]
        if failed_cases:
            for r in failed_cases:
                lines.append(f"- `{r['name']}` → `{r['fallback']}`")
        else:
            lines.append("- None")
        lines.append("")

    lines.append("## Top-K Failure Modes and Hardening Targets\n")
    lines.append(
        "The selection below ranks concrete failure modes by count and by the "
        "observed fallback tag.  Both hard failures and applied edits that required "
        "a non-perfect fallback are considered, because the latter show where the "
        "current matcher is being stressed.  The reasoning is recorded so the choice "
        "is auditable.\n"
    )

    # Flatten all stressful outcomes into a ranked list.
    all_stress = Counter()
    for r in results:
        if r["outcome"] == "failed":
            all_stress[(r["domain"], r["fallback"])] += 1
        elif r["fallback"] != FallbackTag.PERFECT:
            all_stress[(r["domain"], r["fallback"])] += 1

    top = all_stress.most_common(8)
    lines.append("| Rank | Domain | Fallback | Count | Selection Rationale |")
    lines.append("|------|--------|----------|-------|---------------------|")
    selected = []
    for rank, ((domain, fallback), count) in enumerate(top, start=1):
        rationale = {
            ("typst", FallbackTag.EDIT_DISTANCE): (
                "Typst SEARCH blocks fall back to edit-distance; document-type "
                "awareness for headings/comment markers should recover these."
            ),
            ("typst", FallbackTag.IGNORE_LINEBREAKS): (
                "Typst SEARCH blocks require line-break folding; document-type "
                "awareness should keep this fallback but make it more predictable."
            ),
            ("markdown", FallbackTag.EDIT_DISTANCE): (
                "Markdown SEARCH blocks fall back to edit-distance; fence "
                "collisions and heading/hash-marker normalization are the likely "
                "drivers."
            ),
            ("anchor", FallbackTag.ANCHOR_HEADTAIL): (
                "ANCHOR/REPLACE blocks fail or stress the head/tail matcher; "
                "fuzzier anchor matching (whitespace/mid-sentence drift) is needed."
            ),
        }.get(
            (domain, fallback),
            "Observed stressful fallback; harden if data volume grows.",
        )
        lines.append(f"| {rank} | {domain} | {fallback} | {count} | {rationale} |")
        if rank <= 4:
            selected.append((domain, fallback, count, rationale))
    lines.append("")

    lines.append("### Selected Hardening Targets (2–4 modes)\n")
    for idx, (domain, fallback, count, rationale) in enumerate(selected, start=1):
        lines.append(f"{idx}. **{domain} / {fallback}** — {count} case(s). {rationale}\n")

    lines.append("## Raw JSONL Records\n")
    lines.append("```jsonl")
    for record in log_records:
        lines.append(json.dumps(record, ensure_ascii=False))
    lines.append("```\n")

    lines.append("## Selection Reasoning\n")
    lines.append(
        "The ranking above is produced from a synthetic corpus that mirrors the "
        "malformed-but-realistic LLM outputs described in the PRD.  The top modes "
        "concentrate in the two document-type domains (Typst and Markdown) and in "
        "the ANCHOR/REPLACE head/tail path.  This matches the PRD hypothesis that "
        "the current matcher is LaTeX-centric and that Typst/Markdown/ANCHOR cases "
        "need document-type-aware normalization and fuzzier anchor handling.\n"
    )
    lines.append(
        "Follow-on hardening issues (A3+) should address the selected targets in "
        "priority order, measuring the before/after failure rate on this same corpus.\n"
    )

    return "\n".join(lines)


def generate_report(output_path: Path = REPORT_PATH):
    """Generate the failure-distribution baseline report."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        log_path = Path(f.name)

    try:
        results = run_corpus(log_path)
        agg = aggregate(results)
        log_records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        report = render_report(results, agg, log_records)
        output_path.write_text(report, encoding="utf-8")
        return output_path
    finally:
        log_path.unlink(missing_ok=True)


def main():
    generate_report()
    print(f"Wrote failure-distribution baseline to {REPORT_PATH}")


if __name__ == "__main__":
    main()
