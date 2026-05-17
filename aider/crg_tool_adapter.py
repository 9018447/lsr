"""
Adapter for integrating crg_toolkit.py into aider's LLM workflow.

Provides:
- CRG_TOOL_PROMPT: system prompt snippet that teaches the LLM to emit <crg_tool> tags.
- parse_crg_tags(): extracts <crg_tool> XML tags from assistant text.
- run_crg_tool(): safely executes crg_toolkit.py subcommands via direct Python calls.
- execute_crg_tools(): batch runner that parses tags, executes them, and formats results.
- ensure_graph_db(): auto-builds the graph database if missing.
"""

from __future__ import annotations

import io
import re
import shlex
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

CRG_BASE_PROMPT = """\
You have access to a local code-review-graph database (.code-review-graph/graph.db).
The following XML tags invoke CRG toolkit commands. Place them in your response to execute them:

<crg_tool subcommand="query" args="SYMBOL [--callers] [--callees] [--tests] [--limit N]" />
<crg_tool subcommand="search" args="PATTERN [--limit N]" />
<crg_tool subcommand="impact" args="FILE1 [FILE2 ...] [--limit N]" />
<crg_tool subcommand="flows" args="[--top N]" />
<crg_tool subcommand="risk" args="[--top N]" />
<crg_tool subcommand="communities" args="[--detail NAME]" />
<crg_tool subcommand="status" args="" />

## IMPORTANT RULES

1. Each <crg_tool> tag executes ONE command. To search multiple keywords, emit MULTIPLE tags, one per keyword.
2. For `search`, the PATTERN must be a single word or identifier (no spaces). If you need to search multiple concepts, use separate tags.

## EXAMPLES

Good (one search per keyword):
<crg_tool subcommand="search" args="hashline" />
<crg_tool subcommand="search" args="agent" />

Bad (multiple keywords in one search):
<crg_tool subcommand="search" args="hashline agent code-review" />

Good (query with options):
<crg_tool subcommand="query" args="value --callers --callees --limit 10" />

Results are returned automatically.
"""

CRG_PLAN_PROMPT = (
    CRG_BASE_PROMPT
    + "\n\nMANDATORY: Before writing any plan, you MUST use at least 2 CRG tools to explore callers, callees, or impact."
)

CRG_ASK_PROMPT = (
    CRG_BASE_PROMPT
    + "\n\nUse CRG tools proactively to provide evidence-based answers about code relationships."
)

CRG_CODE_PROMPT = (
    CRG_BASE_PROMPT
    + "\n\nIf you encounter unexpected code behavior or need to verify call chains, use CRG tools on-the-fly."
)

CRG_ARCHITECT_PROMPT = (
    CRG_BASE_PROMPT
    + "\n\nBefore designing changes, use CRG tools to analyze execution flows and risk hotspots."
)

# Backward compatibility alias
CRG_TOOL_PROMPT = CRG_BASE_PROMPT


def get_crg_prompt_for_mode(mode: str) -> str:
    mapping = {
        "plan": CRG_PLAN_PROMPT,
        "ask": CRG_ASK_PROMPT,
        "code": CRG_CODE_PROMPT,
        "architect": CRG_ARCHITECT_PROMPT,
    }
    return mapping.get(mode, CRG_BASE_PROMPT)

ALLOWED_SUBCOMMANDS = {
    "status",
    "query",
    "search",
    "flows",
    "communities",
    "risk",
    "impact",
    "export",
    "wiki",
}

_MAX_OUTPUT_LEN = 8192
_BUILD_TIMEOUT = 120

_HANDLERS = {
    "status": "cmd_status",
    "query": "cmd_query",
    "search": "cmd_search",
    "flows": "cmd_flows",
    "communities": "cmd_communities",
    "risk": "cmd_risk",
    "impact": "cmd_impact",
    "export": "cmd_export",
    "wiki": "cmd_wiki",
}


def ensure_graph_db(root: str | Path) -> bool:
    """Ensure .code-review-graph/graph.db exists, building it if necessary.

    Returns True if the database exists (or was successfully built).
    """
    db_path = Path(root) / ".code-review-graph/graph.db"
    if db_path.exists():
        return True

    try:
        result = subprocess.run(
            ["code-review-graph", "build"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=_BUILD_TIMEOUT,
        )
    except FileNotFoundError:
        # code-review-graph binary not installed or not on PATH
        return False
    except subprocess.TimeoutExpired:
        return False

    return db_path.exists()


def parse_crg_tags(content: str) -> list[dict]:
    """Extract <crg_tool subcommand=... args=... /> tags from LLM output.

    Returns a list of dicts with keys 'subcommand' and 'args'.
    """
    if not content:
        return []

    pattern = re.compile(
        r'<crg_tool\s+subcommand=["\']([^"\']+)["\']\s+args=["\']([^"\']*)["\']\s*/>',
        re.IGNORECASE,
    )
    matches = []
    for m in pattern.finditer(content):
        matches.append({"subcommand": m.group(1), "args": m.group(2)})
    return matches


def run_crg_tool(subcommand: str, args_str: str, root: str | Path) -> str:
    """Execute a single crg_toolkit.py subcommand safely via direct Python call.

    Returns captured stdout+stderr capped at _MAX_OUTPUT_LEN characters.
    """
    if subcommand not in ALLOWED_SUBCOMMANDS:
        return (
            f"Error: invalid crg_tool subcommand '{subcommand}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_SUBCOMMANDS))}"
        )

    try:
        tokens = shlex.split(args_str) if args_str.strip() else []
    except ValueError as exc:
        return f"Error parsing args: {exc}"

    from aider.crg_common import load_code_map
    from aider.crg_toolkit import _build_parser
    from aider import crg_toolkit as crg_mod

    parser = _build_parser()
    # Capture argparse errors by redirecting stderr during parse_args
    parse_err = io.StringIO()
    with redirect_stderr(parse_err):
        try:
            ns = parser.parse_args([subcommand] + tokens)
        except SystemExit:
            err_msg = parse_err.getvalue().strip()
            hint = ""
            if subcommand == "search" and len(tokens) > 1:
                hint = "\nHint: `search` accepts only one PATTERN. Use multiple <crg_tool> tags for multiple keywords."
            return f"Error parsing arguments for /crg {subcommand}: {err_msg or 'invalid arguments'}{hint}"

    try:
        db_path = str(Path(root) / ".code-review-graph/graph.db")
        cm = load_code_map(db_path)
    except FileNotFoundError as e:
        return f"Error loading code map: {e}"
    except Exception as e:
        return f"Error: {e}"

    handler_name = _HANDLERS[subcommand]
    handler = getattr(crg_mod, handler_name)

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        try:
            handler(cm, ns)
        except SystemExit:
            pass  # argparse or cmd_* may call sys.exit

    output = out_buf.getvalue()
    stderr_output = err_buf.getvalue()
    if stderr_output:
        output += "\n" + stderr_output

    if len(output) > _MAX_OUTPUT_LEN:
        output = output[:_MAX_OUTPUT_LEN] + "\n… (truncated)"

    return output


def execute_crg_tools(content: str, root: str | Path) -> str | None:
    """Parse <crg_tool> tags in *content*, run them, and return a combined result string.

    Returns None if no tags are found.
    """
    tags = parse_crg_tags(content)
    if not tags:
        return None

    if not ensure_graph_db(root):
        return (
            "The code-review-graph database is missing and could not be built "
            "(code-review-graph build failed or is not installed)."
        )

    parts = []
    for tag in tags:
        subcommand = tag["subcommand"]
        args = tag["args"]
        out = run_crg_tool(subcommand, args, root)
        parts.append(f"### crg {subcommand} {args}\n{out}")

    return "\n\n".join(parts)
