"""
crg_common.py
Shared database access layer for code-review-graph CLI tools.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_DB = "@.code-review-graph/graph.db"
MIN_EDGE_CONFIDENCE = 0.25


@dataclass
class Node:
    id: int
    kind: str
    name: str
    qualified_name: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    parent_name: str | None
    params: str | None
    return_type: str | None
    modifiers: str | None
    is_test: bool
    community_id: int | None
    extra: dict
    signature: str | None

    @property
    def display_name(self) -> str:
        return self.name or self.qualified_name.split("::")[-1].split("/")[-1]

    @property
    def short_path(self) -> str:
        p = self.file_path
        if "/" in p:
            parts = p.split("/")
            return "/".join(parts[-3:]) if len(parts) > 3 else p
        return p


@dataclass
class Edge:
    id: int
    kind: str
    source: str
    target: str
    file_path: str | None
    line: int | None
    confidence: float
    confidence_tier: str


@dataclass
class Community:
    id: int
    name: str
    level: int
    parent_id: int | None
    cohesion: float
    size: int
    dominant_language: str
    description: str
    purpose: str | None
    key_symbols: list[str]
    risk: str | None


@dataclass
class Flow:
    id: int
    name: str
    entry_point: str
    criticality: float
    node_count: int
    file_count: int
    critical_path: list[str]


@dataclass
class RiskItem:
    node_id: int
    qualified_name: str
    risk_score: float
    caller_count: int
    test_coverage: str | None
    security_relevant: bool


@dataclass
class CodeMap:
    metadata: dict[str, str]
    nodes: list[Node]
    edges: list[Edge]
    communities: list[Community]
    flows: list[Flow]
    risks: list[RiskItem]
    node_by_qn: dict[str, Node] = field(default_factory=dict)
    node_by_id: dict[int, Node] = field(default_factory=dict)
    nodes_by_file_path: dict[str, list[Node]] = field(default_factory=lambda: defaultdict(list))
    edges_by_source: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    edges_by_target: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    edges_by_kind: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))


def resolve_db_path(db_path: str | None = None) -> str:
    if db_path and Path(db_path).exists():
        return db_path
    alt = Path(".code-review-graph/graph.db")
    if alt.exists():
        return str(alt)
    raise FileNotFoundError(f"Database not found: {db_path or DEFAULT_DB}")


def load_code_map(db_path: str | None = None) -> CodeMap:
    db_path = resolve_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Metadata
    cur.execute("SELECT key, value FROM metadata")
    metadata = {row["key"]: row["value"] for row in cur.fetchall()}

    # Nodes
    nodes: list[Node] = []
    cur.execute(
        """
        SELECT id, kind, name, qualified_name, file_path, line_start, line_end,
               language, parent_name, params, return_type, modifiers, is_test,
               extra, community_id, signature
        FROM nodes
        """
    )
    for row in cur.fetchall():
        extra = json.loads(row["extra"]) if row["extra"] else {}
        nodes.append(
            Node(
                id=row["id"],
                kind=row["kind"],
                name=row["name"] or "",
                qualified_name=row["qualified_name"],
                file_path=row["file_path"] or "",
                line_start=row["line_start"] or 0,
                line_end=row["line_end"] or 0,
                language=row["language"] or "",
                parent_name=row["parent_name"],
                params=row["params"],
                return_type=row["return_type"],
                modifiers=row["modifiers"],
                is_test=bool(row["is_test"]),
                community_id=row["community_id"],
                extra=extra,
                signature=row["signature"],
            )
        )

    # Edges
    edges: list[Edge] = []
    cur.execute(
        """
        SELECT id, kind, source_qualified, target_qualified, file_path, line,
               confidence, confidence_tier
        FROM edges
        WHERE confidence >= ?
        """,
        (MIN_EDGE_CONFIDENCE,),
    )
    for row in cur.fetchall():
        edges.append(
            Edge(
                id=row["id"],
                kind=row["kind"],
                source=row["source_qualified"],
                target=row["target_qualified"],
                file_path=row["file_path"],
                line=row["line"],
                confidence=row["confidence"] or 0.5,
                confidence_tier=row["confidence_tier"] or "medium",
            )
        )

    # Communities
    communities: list[Community] = []
    cur.execute(
        """
        SELECT c.id, c.name, c.level, c.parent_id, c.cohesion, c.size,
               c.dominant_language, c.description,
               cs.purpose, cs.key_symbols, cs.risk
        FROM communities c
        LEFT JOIN community_summaries cs ON cs.community_id = c.id
        """
    )
    for row in cur.fetchall():
        key_symbols = []
        if row["key_symbols"]:
            try:
                key_symbols = json.loads(row["key_symbols"])
            except Exception:
                key_symbols = [row["key_symbols"]]
        communities.append(
            Community(
                id=row["id"],
                name=row["name"],
                level=row["level"],
                parent_id=row["parent_id"],
                cohesion=row["cohesion"] or 0.0,
                size=row["size"],
                dominant_language=row["dominant_language"] or "",
                description=row["description"] or "",
                purpose=row["purpose"],
                key_symbols=key_symbols,
                risk=row["risk"],
            )
        )

    # Flows
    flows: list[Flow] = []
    cur.execute(
        """
        SELECT flow_id, name, entry_point, criticality, node_count, file_count, critical_path
        FROM flow_snapshots
        """
    )
    for row in cur.fetchall():
        path = []
        if row["critical_path"]:
            try:
                path = json.loads(row["critical_path"])
            except Exception:
                path = [row["critical_path"]]
        flows.append(
            Flow(
                id=row["flow_id"],
                name=row["name"],
                entry_point=row["entry_point"],
                criticality=row["criticality"] or 0.0,
                node_count=row["node_count"],
                file_count=row["file_count"],
                critical_path=path,
            )
        )

    # Risks
    risks: list[RiskItem] = []
    cur.execute(
        """
        SELECT node_id, qualified_name, risk_score, caller_count, test_coverage, security_relevant
        FROM risk_index
        WHERE risk_score >= 0.3
        ORDER BY risk_score DESC
        """
    )
    for row in cur.fetchall():
        risks.append(
            RiskItem(
                node_id=row["node_id"],
                qualified_name=row["qualified_name"],
                risk_score=row["risk_score"],
                caller_count=row["caller_count"],
                test_coverage=row["test_coverage"],
                security_relevant=bool(row["security_relevant"]),
            )
        )

    conn.close()

    # Build indexes
    node_by_qn: dict[str, Node] = {}
    node_by_id: dict[int, Node] = {}
    nodes_by_file_path: dict[str, list[Node]] = defaultdict(list)
    edges_by_source: dict[str, list[Edge]] = defaultdict(list)
    edges_by_target: dict[str, list[Edge]] = defaultdict(list)
    edges_by_kind: dict[str, list[Edge]] = defaultdict(list)

    for n in nodes:
        node_by_qn[n.qualified_name] = n
        node_by_id[n.id] = n
        if n.file_path:
            nodes_by_file_path[n.file_path].append(n)

    seen_edges: set[tuple[str, str, str]] = set()
    for e in edges:
        key = (e.kind, e.source, e.target)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges_by_source[e.source].append(e)
        edges_by_target[e.target].append(e)
        edges_by_kind[e.kind].append(e)

    return CodeMap(
        metadata=metadata,
        nodes=nodes,
        edges=edges,
        communities=communities,
        flows=flows,
        risks=risks,
        node_by_qn=node_by_qn,
        node_by_id=node_by_id,
        nodes_by_file_path=nodes_by_file_path,
        edges_by_source=edges_by_source,
        edges_by_target=edges_by_target,
        edges_by_kind=edges_by_kind,
    )


def fuzzy_find_node(cm: CodeMap, pattern: str) -> Node | None:
    """Find a node by exact qualified name, then by name, then by substring."""
    if pattern in cm.node_by_qn:
        return cm.node_by_qn[pattern]
    # Exact name match
    for n in cm.nodes:
        if n.name == pattern:
            return n
    # Substring in qualified_name
    matches = [n for n in cm.nodes if pattern.lower() in n.qualified_name.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer Function/Class over File
        for n in matches:
            if n.kind in ("Function", "Class"):
                return n
        return matches[0]
    return None


def get_callers(cm: CodeMap, qn: str) -> list[Edge]:
    return [e for e in cm.edges_by_target.get(qn, []) if e.kind == "CALLS"]


def get_callees(cm: CodeMap, qn: str) -> list[Edge]:
    return [e for e in cm.edges_by_source.get(qn, []) if e.kind == "CALLS"]


def get_tests_for_node(cm: CodeMap, qn: str) -> list[Edge]:
    return [e for e in cm.edges_by_target.get(qn, []) if e.kind == "TESTED_BY"]


def get_imports(cm: CodeMap, qn: str) -> list[Edge]:
    return [e for e in cm.edges_by_source.get(qn, []) if e.kind == "IMPORTS_FROM"]


def get_impacted_nodes(cm: CodeMap, file_paths: list[str]) -> dict[str, Any]:
    """Blast-radius analysis: given changed files, find affected nodes and flows."""
    changed_nodes: list[Node] = []
    for fp in file_paths:
        changed_nodes.extend(cm.nodes_by_file_path.get(fp, []))

    # Direct callers of changed functions
    direct_callers: set[str] = set()
    for n in changed_nodes:
        if n.kind in ("Function", "Class"):
            for e in cm.edges_by_target.get(n.qualified_name, []):
                if e.kind == "CALLS":
                    direct_callers.add(e.source)

    # Flows that touch changed files
    affected_flows: list[Flow] = []
    for fl in cm.flows:
        # Simple heuristic: if entry point is in changed file or path contains changed nodes
        entry_node = cm.node_by_qn.get(fl.entry_point)
        if entry_node and entry_node.file_path in file_paths:
            affected_flows.append(fl)
        else:
            for step in fl.critical_path:
                step_node = cm.node_by_qn.get(step)
                if step_node and step_node.file_path in file_paths:
                    affected_flows.append(fl)
                    break

    # Risk score sum
    risk_sum = sum(
        r.risk_score for r in cm.risks
        if any(r.qualified_name == n.qualified_name for n in changed_nodes)
    )

    return {
        "changed_nodes": changed_nodes,
        "direct_callers": sorted(direct_callers),
        "affected_flows": affected_flows,
        "risk_sum": risk_sum,
    }
