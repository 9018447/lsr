"""
crg_toolkit.py
==============
Unified CLI toolkit for code-review-graph databases.
Replaces MCP tools with direct SQLite queries.

Subcommands:
    status       Graph statistics and health
    query        Query callers, callees, tests, imports for a symbol
    search       Search nodes by name, qualified name, or file path
    flows        List execution flows sorted by criticality
    communities  List communities or show details for one
    risk         Show risk hotspots
    impact       Blast-radius analysis for changed files
    export       Export full code map to Markdown
    wiki         Generate wiki pages from communities

Usage:
    python crg_toolkit.py status
    python crg_toolkit.py query value --callers --callees
    python crg_toolkit.py search partials
    python crg_toolkit.py flows --top 10
    python crg_toolkit.py impact src/dual.jl src/partials.jl
    python crg_toolkit.py export -o code_map.md
    python crg_toolkit.py wiki --output wiki/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aider.crg_common import (
    CodeMap,
    load_code_map,
    fuzzy_find_node,
    get_callers,
    get_callees,
    get_tests_for_node,
    get_imports,
    get_impacted_nodes,
    resolve_db_path,
)


def fmt_qn(qn: str, max_len: int = 60) -> str:
    short = qn.split("::")[-1] if "::" in qn else qn.split("/")[-1]
    return short[:max_len]


def fmt_node(n) -> str:
    sig = f"{n.display_name}({n.params or ''})"
    if n.return_type:
        sig += f" -> {n.return_type}"
    return f"{n.kind} {sig}  ({n.short_path}:{n.line_start})"


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------
def cmd_status(cm: CodeMap, args: argparse.Namespace) -> int:
    total_nodes = len(cm.nodes)
    total_edges = len(cm.edges)
    kinds = {}
    for n in cm.nodes:
        kinds[n.kind] = kinds.get(n.kind, 0) + 1
    edge_kinds = {}
    for e in cm.edges:
        edge_kinds[e.kind] = edge_kinds.get(e.kind, 0) + 1

    print("Graph Status")
    print("=" * 40)
    print(f"  Branch:        {cm.metadata.get('git_branch', 'unknown')}")
    print(f"  Commit:        {cm.metadata.get('git_head_sha', 'unknown')[:12]}")
    print(f"  Last updated:  {cm.metadata.get('last_updated', 'unknown')}")
    print()
    print(f"  Nodes:         {total_nodes}")
    for k, c in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"    {k:12s} {c}")
    print()
    print(f"  Edges:         {total_edges}")
    for k, c in sorted(edge_kinds.items(), key=lambda x: -x[1]):
        print(f"    {k:12s} {c}")
    print()
    print(f"  Communities:   {len(cm.communities)}")
    print(f"  Flows:         {len(cm.flows)}")
    print(f"  Risks (>=0.3): {len(cm.risks)}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: query
# ---------------------------------------------------------------------------
def cmd_query(cm: CodeMap, args: argparse.Namespace) -> int:
    node = fuzzy_find_node(cm, args.symbol)
    if not node:
        print(f"Symbol not found: {args.symbol}", file=sys.stderr)
        return 1

    print(f"Symbol: {node.qualified_name}")
    print(f"  Kind: {node.kind}")
    print(f"  File: {node.file_path}:{node.line_start}-{node.line_end}")
    print(f"  Language: {node.language}")
    if node.community_id:
        comm = next((c for c in cm.communities if c.id == node.community_id), None)
        if comm:
            print(f"  Community: {comm.name}")
    print()

    if args.callers:
        edges = get_callers(cm, node.qualified_name)
        print(f"Callers ({len(edges)}):")
        for e in edges[: args.limit]:
            print(f"  <- {fmt_qn(e.source)}  [conf={e.confidence:.2f}]")
        if len(edges) > args.limit:
            print(f"  ... and {len(edges) - args.limit} more")
        print()

    if args.callees:
        edges = get_callees(cm, node.qualified_name)
        print(f"Callees ({len(edges)}):")
        for e in edges[: args.limit]:
            print(f"  -> {fmt_qn(e.target)}  [conf={e.confidence:.2f}]")
        if len(edges) > args.limit:
            print(f"  ... and {len(edges) - args.limit} more")
        print()

    if args.tests:
        edges = get_tests_for_node(cm, node.qualified_name)
        print(f"Tests ({len(edges)}):")
        for e in edges[: args.limit]:
            print(f"  [test] {fmt_qn(e.source)}")
        if len(edges) > args.limit:
            print(f"  ... and {len(edges) - args.limit} more")
        print()

    if args.imports:
        edges = get_imports(cm, node.qualified_name)
        print(f"Imports ({len(edges)}):")
        for e in edges[: args.limit]:
            print(f"  import {fmt_qn(e.target)}")
        if len(edges) > args.limit:
            print(f"  ... and {len(edges) - args.limit} more")
        print()

    return 0


# ---------------------------------------------------------------------------
# Subcommand: search
# ---------------------------------------------------------------------------


def _search_relevance_score(node, pattern: str) -> int:
    """Score a node's relevance to a search pattern. Higher = more relevant."""
    name_lower = node.name.lower()
    qn_lower = node.qualified_name.lower()

    # Exact name match = highest
    if name_lower == pattern:
        return 100
    # Name starts with pattern
    if name_lower.startswith(pattern):
        return 80
    # Name contains pattern
    if pattern in name_lower:
        return 60
    # Qualified name contains pattern
    if pattern in qn_lower:
        return 40
    # File path contains pattern (lowest)
    return 20


def _fuzzy_match_score(text: str, pattern: str) -> float:
    """Calculate fuzzy match score using SequenceMatcher. Returns 0.0-1.0."""
    from difflib import SequenceMatcher

    if not text or not pattern:
        return 0.0
    return SequenceMatcher(None, text, pattern).ratio()


def _fuzzy_search(nodes, pattern: str, threshold: float = 0.6):
    """Fuzzy search nodes, returning (node, score) tuples above threshold."""
    results = []
    for n in nodes:
        name_score = _fuzzy_match_score(n.name.lower(), pattern)
        qn_score = _fuzzy_match_score(n.qualified_name.lower(), pattern)
        best_score = max(name_score, qn_score)
        if best_score >= threshold:
            results.append((n, best_score))
    results.sort(key=lambda x: -x[1])
    return results


def _print_context(node, num_lines: int = 3):
    """Print surrounding code context for a node."""
    try:
        file_path = Path(node.file_path)
        if not file_path.exists():
            return
        with open(file_path) as f:
            lines = f.readlines()
        start = max(0, node.line_start - 1 - num_lines)
        end = min(len(lines), node.line_start - 1 + num_lines)
        for i in range(start, end):
            marker = ">>>" if i == node.line_start - 1 else "   "
            print(f"             {marker} {i + 1:4d} | {lines[i].rstrip()}")
    except (OSError, AttributeError):
        pass


def cmd_search(cm: CodeMap, args: argparse.Namespace) -> int:
    pattern = args.pattern.lower()
    fuzzy = getattr(args, "fuzzy", False)
    threshold = getattr(args, "threshold", 0.6)
    context_lines = getattr(args, "context", 0)
    use_regex = getattr(args, "regex", False)
    results = []

    if use_regex:
        # Regex matching mode
        import re

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            print(f"Invalid regex pattern: {e}", file=sys.stderr)
            return 1

        for n in cm.nodes:
            if (
                regex.search(n.name)
                or regex.search(n.qualified_name)
                or regex.search(n.file_path)
            ):
                results.append(n)
    elif fuzzy:
        # Fuzzy matching mode
        fuzzy_results = _fuzzy_search(cm.nodes, pattern, threshold)
        for n, _score in fuzzy_results:
            results.append(n)
    else:
        # Exact substring matching mode
        for n in cm.nodes:
            if (
                pattern in n.name.lower()
                or pattern in n.qualified_name.lower()
                or pattern in n.file_path.lower()
            ):
                results.append(n)

    if not results:
        print(f"No matches for: {args.pattern}")
        return 0

    # Sort by relevance: exact name > name start > name contains > qn contains > path contains
    results.sort(key=lambda n: -_search_relevance_score(n, pattern))

    print(f"Found {len(results)} match(es) for '{args.pattern}':")
    print()
    for n in results[: args.limit]:
        print(f"  [{n.kind:8s}] {n.display_name:30s}  {n.short_path}:{n.line_start}")
        print(f"             qn: {n.qualified_name}")
        if context_lines and n.file_path:
            _print_context(n, context_lines)
    if len(results) > args.limit:
        print(f"  ... and {len(results) - args.limit} more")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: flows
# ---------------------------------------------------------------------------
def cmd_flows(cm: CodeMap, args: argparse.Namespace) -> int:
    flows = sorted(cm.flows, key=lambda f: -f.criticality)
    if args.flow_name:
        flows = [f for f in flows if args.flow_name.lower() in f.name.lower()]

    print(f"Execution Flows (showing top {args.limit}):")
    print()
    for fl in flows[: args.limit]:
        print(f"  {fl.name}")
        print(f"    Entry:      {fmt_qn(fl.entry_point)}")
        print(f"    Criticality: {fl.criticality:.2f}")
        print(f"    Nodes:      {fl.node_count} across {fl.file_count} file(s)")
        if fl.critical_path:
            path_str = " -> ".join(fmt_qn(s) for s in fl.critical_path[:8])
            print(f"    Path:       {path_str}")
            if len(fl.critical_path) > 8:
                print(f"                ... ({len(fl.critical_path) - 8} more)")
        print()
    return 0


# ---------------------------------------------------------------------------
# Subcommand: communities
# ---------------------------------------------------------------------------
def cmd_communities(cm: CodeMap, args: argparse.Namespace) -> int:
    if args.detail:
        comm = next(
            (
                c
                for c in cm.communities
                if c.name == args.detail or str(c.id) == args.detail
            ),
            None,
        )
        if not comm:
            print(f"Community not found: {args.detail}", file=sys.stderr)
            return 1
        print(f"Community: {comm.name}")
        print(f"  ID:       {comm.id}")
        print(f"  Language: {comm.dominant_language}")
        print(f"  Size:     {comm.size}")
        print(f"  Cohesion: {comm.cohesion:.2f}")
        print(f"  Desc:     {comm.description}")
        if comm.purpose:
            print(f"  Purpose:  {comm.purpose}")
        if comm.key_symbols:
            print("  Key symbols:")
            for sym in comm.key_symbols[:10]:
                print(f"    - {sym}")
        print()
        members = [
            n
            for n in cm.nodes
            if n.community_id == comm.id and n.kind in ("Function", "Class")
        ]
        print(f"  Members ({len(members)}):")
        for n in sorted(members, key=lambda x: (x.file_path, x.line_start))[
            : args.limit
        ]:
            print(f"    {fmt_node(n)}")
        if len(members) > args.limit:
            print(f"    ... and {len(members) - args.limit} more")
        return 0

    print("Communities:")
    print()
    for comm in sorted(cm.communities, key=lambda c: -c.size):
        print(
            f"  {comm.name:15s}  lang={comm.dominant_language:8s}  size={comm.size:4d}  cohesion={comm.cohesion:.2f}"
        )
        if args.verbose:
            print(f"    {comm.description}")
            if comm.key_symbols:
                print(f"    Key: {', '.join(str(s) for s in comm.key_symbols[:5])}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: risk
# ---------------------------------------------------------------------------
def cmd_risk(cm: CodeMap, args: argparse.Namespace) -> int:
    risks = cm.risks[: args.limit]
    if not risks:
        print("No risk hotspots found.")
        return 0

    print(f"Risk Hotspots (top {len(risks)}):")
    print()
    print(f"  {'Score':>6s}  {'Callers':>7s}  {'Security':>8s}  Symbol")
    print(f"  {'-' * 6}  {'-' * 7}  {'-' * 8}  {'-' * 40}")
    for r in risks:
        sec = "YES" if r.security_relevant else "no"
        name = fmt_qn(r.qualified_name, 50)
        print(f"  {r.risk_score:6.2f}  {r.caller_count:7d}  {sec:>8s}  {name}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: impact
# ---------------------------------------------------------------------------
def _resolve_impact_files(cm: CodeMap, patterns: list[str]) -> list[str]:
    """Match user-provided file patterns against absolute paths in DB."""
    matched: set[str] = set()
    all_fps = set(cm.nodes_by_file_path.keys())
    for pat in patterns:
        pat_lower = pat.lower()
        for fp in all_fps:
            if pat in fp or pat_lower in fp.lower() or fp.endswith(pat):
                matched.add(fp)
    return sorted(matched)


def cmd_impact(cm: CodeMap, args: argparse.Namespace) -> int:
    files = _resolve_impact_files(cm, args.files)
    if not files:
        print("No files matched the given patterns.", file=sys.stderr)
        return 1
    result = get_impacted_nodes(cm, files)

    print("Change Impact Analysis")
    print("=" * 40)
    print(f"Changed files: {len(files)}")
    for f in files:
        print(f"  - {f}")
    print()

    changed = result["changed_nodes"]
    print(f"Changed nodes: {len(changed)}")
    for n in changed[: args.limit]:
        print(f"  {fmt_node(n)}")
    if len(changed) > args.limit:
        print(f"  ... and {len(changed) - args.limit} more")
    print()

    callers = result["direct_callers"]
    print(f"Direct callers affected: {len(callers)}")
    for c in callers[: args.limit]:
        print(f"  <- {fmt_qn(c)}")
    if len(callers) > args.limit:
        print(f"  ... and {len(callers) - args.limit} more")
    print()

    flows = result["affected_flows"]
    print(f"Affected execution flows: {len(flows)}")
    for fl in sorted(flows, key=lambda f: -f.criticality)[: args.limit]:
        print(f"  {fl.name}  (criticality={fl.criticality:.2f})")
    if len(flows) > args.limit:
        print(f"  ... and {len(flows) - args.limit} more")
    print()

    print(f"Aggregated risk score: {result['risk_sum']:.2f}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: export
# ---------------------------------------------------------------------------
def cmd_export(cm: CodeMap, args: argparse.Namespace) -> int:
    # Delegate to export_code_map.py logic if available, else warn
    export_script = Path(__file__).with_name("export_code_map.py")
    if export_script.exists():
        import subprocess

        cmd = [sys.executable, str(export_script), "-o", args.output]
        if args.llm:
            cmd.append("--llm")
        if args.db:
            cmd.extend(["--db", args.db])
        return subprocess.call(cmd)
    else:
        print("export_code_map.py not found; please run it directly.", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Subcommand: wiki
# ---------------------------------------------------------------------------
def cmd_wiki(cm: CodeMap, args: argparse.Namespace) -> int:
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Index page
    index_lines = ["# Code Wiki", ""]
    index_lines.append("Generated from code-review-graph analysis.")
    index_lines.append("")

    for comm in sorted(cm.communities, key=lambda c: -c.size):
        page_name = f"community_{comm.name}.md"
        page_path = out_dir / page_name

        lines = [f"# Community: {comm.name}", ""]
        lines.append(f"- **Language:** {comm.dominant_language}")
        lines.append(f"- **Size:** {comm.size}")
        lines.append(f"- **Cohesion:** {comm.cohesion:.2f}")
        lines.append(f"- **Description:** {comm.description}")
        if comm.purpose:
            lines.append(f"- **Purpose:** {comm.purpose}")
        if comm.key_symbols:
            lines.append(
                f"- **Key Symbols:** {', '.join(str(s) for s in comm.key_symbols)}"
            )
        lines.append("")

        members = [
            n
            for n in cm.nodes
            if n.community_id == comm.id and n.kind in ("Function", "Class", "Test")
        ]
        lines.append(f"## Members ({len(members)})")
        lines.append("")
        for n in sorted(members, key=lambda x: (x.file_path, x.line_start)):
            sig = f"{n.display_name}({n.params or ''})"
            lines.append(f"- `{n.kind}` {sig} — `{n.short_path}:{n.line_start}`")
        lines.append("")

        # Call graph within community
        internal_calls = []
        for n in members:
            for e in cm.edges_by_source.get(n.qualified_name, []):
                if e.kind == "CALLS":
                    tgt = cm.node_by_qn.get(e.target)
                    if tgt and tgt.community_id == comm.id:
                        internal_calls.append((n.display_name, tgt.display_name))
        if internal_calls:
            lines.append("## Internal Call Graph")
            lines.append("")
            seen = set()
            for src, tgt in internal_calls:
                key = (src, tgt)
                if key not in seen:
                    seen.add(key)
                    lines.append(f"- `{src}` -> `{tgt}`")
            lines.append("")

        page_path.write_text("\n".join(lines), encoding="utf-8")
        index_lines.append(
            f"- [{comm.name}]({page_name}) — {comm.dominant_language}, {comm.size} symbols"
        )

    (out_dir / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    print(f"Wiki generated in {out_dir}/")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crg_toolkit.py",
        description="Code-review-graph CLI toolkit (MCP tool replacement)",
    )
    parser.add_argument("--db", default=None, help="Path to graph.db")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    sub.add_parser("status", help="Graph statistics and health")

    # query
    query_parser = sub.add_parser("query", help="Query symbol relationships")
    query_parser.add_argument("symbol", help="Symbol name or qualified name")
    query_parser.add_argument("--callers", action="store_true", help="Show callers")
    query_parser.add_argument("--callees", action="store_true", help="Show callees")
    query_parser.add_argument("--tests", action="store_true", help="Show tests")
    query_parser.add_argument("--imports", action="store_true", help="Show imports")
    query_parser.add_argument(
        "--limit", type=int, default=20, help="Max results per category"
    )

    # search
    search_parser = sub.add_parser("search", help="Search nodes by name or path")
    search_parser.add_argument("pattern", help="Search pattern")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("-v", "--verbose", action="store_true")
    search_parser.add_argument(
        "--fuzzy", action="store_true", help="Enable fuzzy matching"
    )
    search_parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Fuzzy match threshold (0.0-1.0, default: 0.6)",
    )
    search_parser.add_argument(
        "-c",
        "--context",
        type=int,
        default=0,
        help="Show N lines of code context around each match",
    )
    search_parser.add_argument(
        "-r", "--regex", action="store_true", help="Use regex pattern matching"
    )

    # flows
    flows_parser = sub.add_parser("flows", help="List execution flows")
    flows_parser.add_argument("--top", type=int, default=20, dest="limit")
    flows_parser.add_argument(
        "--name", dest="flow_name", default=None, help="Filter by flow name"
    )

    # communities
    comm_parser = sub.add_parser("communities", help="List or inspect communities")
    comm_parser.add_argument(
        "--detail", default=None, help="Show detail for a community name or ID"
    )
    comm_parser.add_argument("--limit", type=int, default=30)
    comm_parser.add_argument("-v", "--verbose", action="store_true")

    # risk
    risk_parser = sub.add_parser("risk", help="Show risk hotspots")
    risk_parser.add_argument("--top", type=int, default=20, dest="limit")

    # impact
    impact_parser = sub.add_parser(
        "impact", help="Blast-radius analysis for changed files"
    )
    impact_parser.add_argument("files", nargs="+", help="Changed file paths")
    impact_parser.add_argument("--limit", type=int, default=20)

    # export
    export_parser = sub.add_parser("export", help="Export full code map to Markdown")
    export_parser.add_argument("-o", "--output", default="code_map.md")
    export_parser.add_argument("--llm", action="store_true", help="Use LLM refinement")

    # wiki
    wiki_parser = sub.add_parser("wiki", help="Generate markdown wiki from communities")
    wiki_parser.add_argument("--output", default="wiki", help="Output directory")

    return parser


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        db_path = resolve_db_path(args.db)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    print(f"Loading graph from {db_path} ...")
    cm = load_code_map(db_path)
    print(
        f"Loaded {len(cm.nodes)} nodes, {len(cm.edges)} edges, "
        f"{len(cm.communities)} communities, {len(cm.flows)} flows."
    )
    print()

    handlers = {
        "status": cmd_status,
        "query": cmd_query,
        "search": cmd_search,
        "flows": cmd_flows,
        "communities": cmd_communities,
        "risk": cmd_risk,
        "impact": cmd_impact,
        "export": cmd_export,
        "wiki": cmd_wiki,
    }

    handler = handlers.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    return handler(cm, args)


if __name__ == "__main__":
    sys.exit(main())
