# Agent Guide: Code Review Graph Toolkit

This document describes the CLI tools available for analyzing the `ForwardDiff.jl` codebase via the `code-review-graph` SQLite database.

## Prerequisites

The graph database must be built first:

```bash
code-review-graph build
```

This creates `.code-review-graph/graph.db` with nodes, edges, communities, flows, and risk data.

## Tool Inventory

### 1. `crg_toolkit.py` — Unified CLI

A single-entry CLI that replaces the MCP tool suite. All subcommands read from `.code-review-graph/graph.db` directly.

| Subcommand | Purpose |
|------------|---------|
| `status` | Graph health, node/edge counts, metadata |
| `query <symbol>` | Inspect callers, callees, tests, imports for a symbol |
| `search <pattern>` | Fuzzy search nodes by name, qualified name, or file path |
| `flows` | List execution flows sorted by criticality |
| `communities` | List or inspect code communities (modules) |
| `risk` | Top risk hotspots by score |
| `impact <files...>` | Blast-radius analysis for changed files |
| `export` | Export full code map to Markdown |
| `wiki` | Generate community wiki pages |

#### Usage Examples

```bash
# Graph overview
python crg_toolkit.py status

# Who calls `value`? What does `value` call?
python crg_toolkit.py query value --callers --callees --limit 10

# Search for anything related to "partials"
python crg_toolkit.py search partials --limit 15

# Top 10 execution flows
python crg_toolkit.py flows --top 10

# Inspect the src-mode community
python crg_toolkit.py communities --detail src-mode --limit 15

# Top 20 risk hotspots
python crg_toolkit.py risk --top 20

# Change impact analysis (paths matched against DB automatically)
python crg_toolkit.py impact src/dual.jl src/partials.jl --limit 10

# Generate full code map
python crg_toolkit.py export -o code_map.md

# Generate community wiki
python crg_toolkit.py wiki --output wiki/
```

### 2. `export_code_map.py` — Narrative Documentation Generator

Produces a human-readable Markdown file covering the full code map. Optionally sends a condensed prompt to an LLM for narrative refinement.

```bash
# Local mode: structured Markdown with tables and sections
python export_code_map.py -o code_map.md

# LLM mode: send condensed graph data to a model for prose documentation
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o"
python export_code_map.py --llm -o code_map.md

# Preview the LLM prompt without calling the API
python export_code_map.py --llm-prompt-only
```

**LLM environment variables:**
- `LLM_API_BASE` — OpenAI-compatible endpoint (default: `https://api.openai.com/v1`)
- `LLM_API_KEY` — API key
- `LLM_MODEL` — Model name (default: `gpt-4o`)

### 3. `crg_common.py` — Shared Library

Not a CLI. Import this in Python scripts to query the graph programmatically.

```python
from crg_common import load_code_map, fuzzy_find_node, get_callers, get_impacted_nodes

cm = load_code_map()
node = fuzzy_find_node(cm, "value")
for e in get_callers(cm, node.qualified_name):
    print(e.source)
```

## Typical Agent Workflows

### Understanding a Symbol
1. `crg_toolkit.py query <symbol> --callers --callees --tests`
2. `crg_toolkit.py search <symbol>` if exact match not found
3. `crg_toolkit.py communities --detail <community>` for module context

### Reviewing a Change
1. `crg_toolkit.py impact <changed-files...> --limit 15`
2. `crg_toolkit.py risk --top 20` to see if hotspots were touched
3. `crg_toolkit.py query <affected-symbols> --tests` to verify test coverage

### Generating Documentation
1. `crg_toolkit.py export -o code_map.md` for structured reference
2. `export_code_map.py --llm -o architecture.md` for narrative prose
3. `crg_toolkit.py wiki --output wiki/` for per-community pages

### Exploring Architecture
1. `crg_toolkit.py status` for overview
2. `crg_toolkit.py communities -v` for module breakdown
3. `crg_toolkit.py flows --top 10` for critical execution paths
4. `crg_toolkit.py risk --top 15` for architectural hotspots

## Database Schema (Key Tables)

| Table | Content |
|-------|---------|
| `nodes` | Symbols (File, Function, Class, Test) with location and metadata |
| `edges` | Relationships (CALLS, CONTAINS, IMPORTS_FROM, INHERITS, REFERENCES, TESTED_BY) |
| `communities` | Detected modules/clusters with cohesion scores |
| `community_summaries` | Purpose, key symbols, risk per community |
| `flows` / `flow_snapshots` | Execution flows with critical paths |
| `risk_index` | Per-node risk scores, caller counts, security flags |
| `metadata` | Build info (branch, SHA, timestamp) |

## Notes

- All tools resolve `.code-review-graph/graph.db` automatically from the current directory.
- The `impact` command accepts partial file paths (e.g., `src/dual.jl`) and matches them against absolute paths stored in the database.
- Edge deduplication and noise filtering (external calls, file-level macro noise) are applied automatically in `crg_common.py`.
- For programmatic access, `crg_common.CodeMap` provides pre-built indexes: `node_by_qn`, `node_by_id`, `nodes_by_file_path`, `edges_by_source`, `edges_by_target`, `edges_by_kind`.
