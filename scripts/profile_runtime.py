#!/usr/bin/env python3
"""Runtime profiling harness for lsr.

Profiles major runtime operations and emits a hotspot report that separates
lsr-internal CPU/time from external waits (compiler subprocess, LLM API).

Usage:
    scripts/profile_runtime.py [--startup-only]
    scripts/profile_runtime.py --profiles startup section_parsing compile lsp chat

Output:
    Writes a human-readable report to stdout.  With --output, also writes the
    report to the given path.
"""

import argparse
import cProfile
import io
import os
import pstats
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

# ---------------------------------------------------------------------------
# Decision logic (pure functions, unit-tested separately)
# ---------------------------------------------------------------------------

ALL_PROFILES = ["startup", "section_parsing", "compile", "lsp", "chat"]


def select_profiles(requested, startup_only):
    """Return the ordered list of profiles to run."""
    if startup_only:
        return ["startup"]
    if requested:
        return [p for p in requested if p in ALL_PROFILES]
    return list(ALL_PROFILES)


def check_prerequisite(profile):
    """Return (ok, reason) for the given profile."""
    if profile == "compile":
        if shutil.which("pdflatex"):
            return True, None
        return False, "pdflatex not on PATH"
    if profile == "lsp":
        if shutil.which("texlab"):
            return True, None
        return False, "texlab not on PATH"
    if profile == "chat":
        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return True, None
        return False, "no OPENAI_API_KEY or ANTHROPIC_API_KEY"
    return True, None


def classify_time(profile, internal_s, external_s):
    """Classify and return a report row dict."""
    return {
        "profile": profile,
        "internal_s": internal_s,
        "external_s": external_s,
        "total_s": internal_s + external_s,
        "internal_pct": (
            internal_s / (internal_s + external_s) * 100 if (internal_s + external_s) > 0 else 0
        ),
    }


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


@contextmanager
def timed():
    """Yield a mutable dict that collects {start, end, elapsed}."""
    bucket = {"start": None, "end": None, "elapsed": None}
    bucket["start"] = time.perf_counter()
    try:
        yield bucket
    finally:
        bucket["end"] = time.perf_counter()
        bucket["elapsed"] = bucket["end"] - bucket["start"]


def profile_function(func, *args, **kwargs):
    """Run func under cProfile and return (result, pstats.Stats)."""
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        result = func(*args, **kwargs)
    finally:
        profiler.disable()
    stats = pstats.Stats(profiler, stream=io.StringIO())
    return result, stats


# ---------------------------------------------------------------------------
# Individual profiles
# ---------------------------------------------------------------------------


def profile_startup():
    """Measure cold-start import and argument-parsing time."""
    # Measure import of the main entry point (this is the dominant cold-start
    # cost for any Python CLI).
    with timed() as import_bucket:
        import lsr.main  # noqa: F401

    # Measure argument parsing without instantiating a Coder.
    with timed() as parse_bucket:
        parser = lsr.args.get_parser([], None)
        parser.parse_known_args(["--exit"])

    # Both phases are lsr-internal; there is no external wait.
    internal = import_bucket["elapsed"] + parse_bucket["elapsed"]
    return classify_time("startup", internal, 0.0), None


def profile_section_parsing():
    """Measure regex-based section parsing for a synthetic manuscript."""
    from lsr.document_types import LATEX

    content = (
        "\\section{Introduction}\n\n"
        "Deep eutectic solvents are promising.\n\n"
        "\\section{Methods}\n\n"
        "We performed DFT calculations.\n\n"
        "\\subsection{Computational Details}\n\n"
        "Gaussian 16 was used.\n\n"
        "\\section{Results}\n\n"
        "The results are shown.\n"
    )

    with timed() as bucket:
        sections = LATEX.parse_sections(content)

    assert len(sections) >= 3
    return classify_time("section_parsing", bucket["elapsed"], 0.0), None


def profile_compile():
    """Measure pdflatex compile, separating lsr overhead from subprocess wait."""
    from lsr.latex_tools import LatexCompiler

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "main.tex"
        tex_path.write_text(
            "\\documentclass{article}\n" "\\begin{document}\n" "Hello world.\n" "\\end{document}\n",
            encoding="utf-8",
        )

        compiler = LatexCompiler(engine="pdflatex", root=tmpdir)

        # Total time through the lsr compile wrapper.
        with timed() as total_bucket:
            success, output, errors = compiler.compile(tex_path)
        assert success, output

        # External time: just the subprocess.run equivalent.
        abs_path = os.path.abspath(tex_path)
        working_dir = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", filename]
        with timed() as external_bucket:
            subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

        internal = max(0.0, total_bucket["elapsed"] - external_bucket["elapsed"])
        return (
            classify_time(
                "compile",
                internal,
                external_bucket["elapsed"],
            ),
            None,
        )


def profile_lsp():
    """Measure LSP server startup time."""
    from lsr.document_types import LATEX
    from lsr.lsp_client import LspClient, path_to_uri

    with tempfile.TemporaryDirectory() as tmpdir:
        client = LspClient()
        command = "texlab"
        args = LATEX.lsp_server.args
        root_uri = path_to_uri(tmpdir)
        init_options = LATEX.lsp_server.initialization_options

        with timed() as internal_bucket:
            pass  # LspClient creation is trivial; startup dominates below.

        with timed() as external_bucket:
            client.start(
                command=command,
                args=args,
                root_uri=root_uri,
                initialization_options=init_options,
            )

        try:
            client.stop()
        except Exception:
            pass

        return (
            classify_time(
                "lsp",
                internal_bucket["elapsed"],
                external_bucket["elapsed"],
            ),
            None,
        )


def profile_chat():
    """Measure chat-send internal overhead around a mocked LLM call."""
    from lsr.models import Model

    # Avoid a real network call; we want to measure lsr overhead, not API latency.
    original_completion = None
    try:
        import litellm

        original_completion = litellm.completion

        def mock_completion(*args, **kwargs):
            # Simulate a small external wait so the harness can separate it.
            time.sleep(0.05)

            class MockChoice:

                class MockMessage:
                    content = "Mocked response."

                message = MockMessage()
                finish_reason = "stop"

            class MockResponse:
                choices = [MockChoice()]

            return MockResponse()

        litellm.completion = mock_completion

        messages = [{"role": "user", "content": "Say hello."}]

        # Internal time: model creation and first-call litellm initialization.
        with timed() as internal_bucket:
            model = Model("gpt-4")
            _hash, response = model.send_completion(messages, functions=None, stream=False)

        # External time: the mocked API wait only.  Subtract the time observed
        # in a no-op call to isolate the wait.
        with timed() as wait_bucket:
            mock_completion()

        external = wait_bucket["elapsed"]
        internal = max(0.0, internal_bucket["elapsed"] - external)

        return (
            classify_time(
                "chat",
                internal,
                external,
            ),
            None,
        )
    finally:
        if original_completion is not None:
            litellm.completion = original_completion


PROFILE_FUNCTIONS = {
    "startup": profile_startup,
    "section_parsing": profile_section_parsing,
    "compile": profile_compile,
    "lsp": profile_lsp,
    "chat": profile_chat,
}


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_report(rows, skipped, cprofile_stats=None):
    """Render a human-readable hotspot report."""
    lines = []
    lines.append("# lsr Runtime Performance Baseline\n")
    lines.append("**Generated by:** `scripts/profile_runtime.py`\n")
    lines.append(
        "**Method:** `time.perf_counter` boundaries separate lsr-internal work "
        "from external waits (compiler subprocess, LLM API round-trip, LSP server "
        "startup).  External waits are measured, not optimized.\n"
    )
    lines.append("| Profile | Internal (s) | External (s) | Total (s) | Internal % |")
    lines.append("|---------|-------------|-------------|-----------|------------|")
    for row in rows:
        lines.append(
            f"| {row['profile']:<15} | {row['internal_s']:.4f} | "
            f"{row['external_s']:.4f} | {row['total_s']:.4f} | "
            f"{row['internal_pct']:.1f}% |"
        )
    lines.append("")

    internal_rows = sorted(rows, key=lambda r: r["internal_s"], reverse=True)
    lines.append("## Top lsr-internal hotspots\n")
    for i, row in enumerate(internal_rows[:3], start=1):
        lines.append(
            f"{i}. `{row['profile']}` — {row['internal_s']:.4f}s internal, "
            f"{row['internal_pct']:.1f}% internal"
        )
    lines.append("")

    lines.append("## Concrete optimization targets\n")
    lines.append(
        "The targets below are derived from the measured hotspots and from the "
        "deferred Phase-3 micro-optimization list.\n"
    )
    for i, row in enumerate(internal_rows[:3], start=1):
        if row["profile"] == "startup":
            target = (
                "Reduce startup cost. Candidate actions: avoid double "
                "`get_parser()` invocation, defer `model_info_manager` singleton "
                "creation, defer cache-dir creation, and defer "
                "`validate_environment` until first model use."
            )
        elif row["profile"] == "chat":
            target = (
                "Reduce first-call litellm/model initialization overhead. "
                "Candidate actions: keep litellm import lazy, avoid eager "
                "model-cost-map fetching, and defer model metadata loading."
            )
        elif row["profile"] == "compile":
            target = (
                "Reduce lsr compile-path overhead. Candidate actions: cache "
                "main-file detection and streamline error parsing."
            )
        else:
            target = "Investigate further with targeted cProfile runs."
        lines.append(f"{i}. `{row['profile']}` — {target}")
    lines.append("")

    if skipped:
        lines.append("## Skipped profiles\n")
        for profile, reason in skipped:
            lines.append(f"- `{profile}`: {reason}")
        lines.append("")

    lines.append(
        "*External waits (compiler subprocess, LLM API, LSP server startup) are "
        "explicitly separated from lsr-internal time and are not optimization "
        "targets for lsr itself.*\n"
    )

    if cprofile_stats is not None:
        lines.append("## cProfile top callers (lsr internals)\n")
        lines.append("```")
        cprofile_stats.sort_stats("cumulative")
        cprofile_stats.print_stats(15)
        lines.append(cprofile_stats.stream.getvalue())
        lines.append("```\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile lsr runtime operations.")
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=ALL_PROFILES,
        help="Profiles to run (default: all).",
    )
    parser.add_argument(
        "--startup-only",
        action="store_true",
        help="Run only the startup profile (no document or API key needed).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the report to this file in addition to stdout.",
    )
    parser.add_argument(
        "--cprofile",
        action="store_true",
        help="Run cProfile over the whole harness and include top callers.",
    )
    args = parser.parse_args(argv)

    profiles = select_profiles(args.profiles, args.startup_only)

    if args.cprofile:
        profiler = cProfile.Profile()
        profiler.enable()

    rows = []
    skipped = []
    for profile in profiles:
        ok, reason = check_prerequisite(profile)
        if not ok:
            skipped.append((profile, reason))
            continue
        row, err = PROFILE_FUNCTIONS[profile]()
        if err:
            skipped.append((profile, err))
            continue
        rows.append(row)

    if args.cprofile:
        profiler.disable()
        stats = pstats.Stats(profiler, stream=io.StringIO())
    else:
        stats = None

    report = render_report(rows, skipped, stats)
    print(report)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
