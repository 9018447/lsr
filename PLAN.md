# Plan: Integrate code-review-graph with Aider via Slash Commands

## Context

The user wants to use `code-review-graph` (CRG) — a persistent incremental knowledge graph for code reviews — as a replacement for aider's built-in repo-map. Aider doesn't support MCP protocol, so we need to:

1. **Add new slash commands** to aider that call CRG's Python API directly (bypassing MCP)
2. **Auto-update CRG's database** whenever aider modifies project code (on edit/commit)

### Key Insight: Direct Python API

CRG exposes all its tools as plain Python functions in `code_review_graph.tools.*`. We can import and call them directly from aider — no MCP, no subprocess needed. This is cleaner and more performant than shelling out to `code-review-graph serve`.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Aider                                 │
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │  Commands.py  │────▶│  crg_commands.py (NEW)           │  │
│  │  cmd_crg_*    │     │  Calls CRG Python API directly   │  │
│  └──────────────┘     └──────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │ base_coder.py │────▶│  auto_commit() hook              │  │
│  │ apply_updates │     │  → CRG incremental update        │  │
│  └──────────────┘     └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐         ┌─────────────────────┐
│  Git Repository  │         │  CRG SQLite DB       │
│                  │         │  (.code-review-graph/) │
└─────────────────┘         └─────────────────────┘
```

---

## Files to Modify

### 1. `aider/crg_bridge.py` (NEW) — CRG Python API Bridge

- Lazy-imports `code_review_graph.tools.*` functions
- Wraps them with error handling and repo_root resolution
- Provides a clean API for both commands and auto-update hooks
- Handles the case where CRG is not installed (graceful fallback)

### 2. `aider/commands.py` (MODIFY) — Add New Slash Commands

Add the following `cmd_crg_*` methods:

| Command                         | CRG Tool                | Description                          |
| ------------------------------- | ----------------------- | ------------------------------------ |
| `/crg-build`                    | `build_or_update_graph` | Build or update the knowledge graph  |
| `/crg-status`                   | `list_graph_stats`      | Show graph statistics                |
| `/crg-impact`                   | `get_impact_radius`     | Analyze blast radius of changes      |
| `/crg-review`                   | `get_review_context`    | Generate focused review context      |
| `/crg-search <query>`           | `semantic_search_nodes` | Search code entities                 |
| `/crg-query <pattern> <target>` | `query_graph`           | Run predefined graph queries         |
| `/crg-communities`              | `list_communities_func` | List code communities                |
| `/crg-flows`                    | `list_flows`            | List execution flows                 |
| `/crg-hubs`                     | `get_hub_nodes_func`    | Find architectural hotspots          |
| `/crg-context`                  | `get_minimal_context`   | Get compact context for current task |
| `/crg-detect`                   | `detect_changes_func`   | Risk-scored change detection         |
| `/crg-wiki`                     | `generate_wiki_func`    | Generate wiki from communities       |
| `/crg-visualize`                | CLI: `visualize`        | Generate HTML visualization          |
| `/crg-watch`                    | `start_watch_thread`    | Start file watcher                   |

### 3. `aider/coders/base_coder.py` (MODIFY) — Auto-Update Hook

- After `auto_commit()` succeeds, trigger CRG incremental update
- After `apply_updates()` (even without commit), trigger CRG update
- Add `--crg-auto-update` / `--no-crg-auto-update` flag
- Use background thread to avoid blocking aider

### 4. `aider/main.py` (MODIFY) — CLI Arguments

- Add `--crg` flag to enable CRG integration
- Add `--crg-auto-update` flag (default: True when --crg is set)
- Add `--crg-data-dir` for custom graph database location

---

## Implementation Details

### Step 1: Create `aider/crg_bridge.py`

```python
"""Bridge module to call code-review-graph Python API directly."""

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_crg_available = None

def is_crg_available():
    """Check if code-review-graph is installed."""
    global _crg_available
    if _crg_available is None:
        try:
            import code_review_graph
            _crg_available = True
        except ImportError:
            _crg_available = False
    return _crg_available

def build_or_update(repo_root, full_rebuild=False, base="HEAD~1"):
    """Build or incrementally update the CRG graph."""
    from code_review_graph.tools import build_or_update_graph
    return build_or_update_graph(
        full_rebuild=full_rebuild,
        repo_root=str(repo_root),
        base=base,
        postprocess="full",
    )

def get_stats(repo_root):
    """Get graph statistics."""
    from code_review_graph.tools import list_graph_stats
    return list_graph_stats(repo_root=str(repo_root))

def get_impact(repo_root, changed_files=None, max_depth=2):
    """Analyze impact radius."""
    from code_review_graph.tools import get_impact_radius
    return get_impact_radius(
        changed_files=changed_files,
        max_depth=max_depth,
        repo_root=str(repo_root),
    )

def get_review(repo_root, changed_files=None, max_depth=2):
    """Get review context."""
    from code_review_graph.tools import get_review_context
    return get_review_context(
        changed_files=changed_files,
        max_depth=max_depth,
        repo_root=str(repo_root),
    )

def search(repo_root, query, kind=None, limit=20):
    """Search code entities."""
    from code_review_graph.tools import semantic_search_nodes
    return semantic_search_nodes(
        query=query, kind=kind, limit=limit,
        repo_root=str(repo_root),
    )

def query(repo_root, pattern, target):
    """Run a predefined graph query."""
    from code_review_graph.tools import query_graph
    return query_graph(
        pattern=pattern, target=target,
        repo_root=str(repo_root),
    )

def auto_update_async(repo_root, base="HEAD~1"):
    """Trigger async incremental update in background thread."""
    if not is_crg_available():
        return
    def _update():
        try:
            result = build_or_update(repo_root, full_rebuild=False, base=base)
            logger.info(f"CRG auto-update: {result}")
        except Exception as e:
            logger.warning(f"CRG auto-update failed: {e}")
    thread = threading.Thread(target=_update, daemon=True)
    thread.start()
    return thread

# ... more wrappers for other tools
```

### Step 2: Add Slash Commands to `aider/commands.py`

Pattern for each command (example):

```python
def cmd_crg_build(self, args):
    """Build or update the code-review-graph knowledge graph"""
    from aider.crg_bridge import is_crg_available, build_or_update
    if not is_crg_available():
        self.io.tool_error("code-review-graph is not installed. Run: pip install code-review-graph")
        return
    if not self.coder.repo:
        self.io.tool_error("No git repository found.")
        return

    full_rebuild = "--full" in args
    result = build_or_update(self.coder.root, full_rebuild=full_rebuild)

    nodes = result.get("total_nodes", 0)
    edges = result.get("total_edges", 0)
    files = result.get("files_parsed", result.get("files_updated", 0))
    self.io.tool_output(f"CRG: {files} files, {nodes} nodes, {edges} edges")
```

### Step 3: Hook Auto-Update into `base_coder.py`

In `auto_commit()` method, after successful commit:

```python
def auto_commit(self, edited, context=None):
    # ... existing code ...
    try:
        res = self.repo.commit(...)
        if res:
            # ... existing code ...

            # NEW: Auto-update CRG after aider edits
            if getattr(self, 'crg_auto_update', False):
                from aider.crg_bridge import auto_update_async
                auto_update_async(self.root)

            return ...
```

### Step 4: Add CLI Args in `main.py`

```python
# In the arg parser section:
parser.add_argument("--crg", action="store_true", help="Enable code-review-graph integration")
parser.add_argument("--crg-auto-update", action="store_true", default=True, help="Auto-update CRG on edits")
parser.add_argument("--no-crg-auto-update", action="store_false", dest="crg_auto_update")

# In the coder initialization:
if args.crg:
    coder.crg_auto_update = args.crg_auto_update
```

---

## Reuse: Existing Code to Leverage

### From code-review-graph (`/home/smh/aider/code-review-graph/`):

- **`code_review_graph/tools/__init__.py`** — All 28 tool functions re-exported
- **`code_review_graph/tools/build.py`** — `build_or_update_graph()`, `run_postprocess()`
- **`code_review_graph/tools/query.py`** — `query_graph()`, `semantic_search_nodes()`, `get_impact_radius()`
- **`code_review_graph/tools/review.py`** — `get_review_context()`, `detect_changes_func()`
- **`code_review_graph/tools/analysis_tools.py`** — Hub/bridge/knowledge gap tools
- **`code_review_graph/tools/community_tools.py`** — Community analysis
- **`code_review_graph/tools/flows_tools.py`** — Execution flow tools
- **`code_review_graph/incremental.py`** — `find_repo_root()`, `get_db_path()`, `start_watch_thread()`
- **`code_review_graph/graph.py`** — `GraphStore` for direct DB access

### From aider (`/home/smh/aider/`):

- **`aider/commands.py`** — Command registration pattern (any `cmd_*` method becomes a slash command)
- **`aider/coders/base_coder.py`** — `auto_commit()` at line ~2423, `apply_updates()` at ~2377
- **`aider/repo.py`** — `GitRepo.commit()` for commit hook
- **`aider/run_cmd.py`** — `run_cmd()` for shell execution

---

## Steps (Implementation Checklist)

- [ ] **Step 1**: Create `aider/crg_bridge.py` — Python API bridge module
  - Lazy imports for all CRG tools
  - Error handling for missing CRG installation
  - Thread-safe async update function
  - JSON output formatting helpers

- [ ] **Step 2**: Add CRG slash commands to `aider/commands.py`
  - Add `cmd_crg_build`, `cmd_crg_status`, `cmd_crg_impact`, `cmd_crg_review`
  - Add `cmd_crg_search`, `cmd_crg_query`, `cmd_crg_communities`, `cmd_crg_flows`
  - Add `cmd_crg_hubs`, `cmd_crg_context`, `cmd_crg_detect`, `cmd_crg_wiki`
  - Add `cmd_crg_visualize`, `cmd_crg_watch`
  - Add `completions_crg_search`, `completions_crg_query` for tab completion

- [ ] **Step 3**: Hook auto-update into `aider/coders/base_coder.py`
  - Add `crg_auto_update` attribute to `Coder.__init__`
  - Hook into `auto_commit()` after successful commit
  - Hook into `apply_updates()` for non-committed edits
  - Use background thread to avoid blocking

- [ ] **Step 4**: Add CLI arguments in `aider/main.py`
  - Add `--crg`, `--crg-auto-update`, `--no-crg-auto-update` flags
  - Wire flags to coder initialization

- [ ] **Step 5**: Add CRG to aider's dependency (optional)
  - Add `code-review-graph` to `pyproject.toml` optional dependencies
  - Or document manual installation

---

## Verification

### Manual Testing:

1. `pip install -e /home/smh/aider` (reinstall aider with changes)
2. Navigate to a git repo with code
3. Run `aider --crg`
4. Test each slash command:
   - `/crg-build` — should build the knowledge graph
   - `/crg-status` — should show graph stats
   - `/crg-search function_name` — should find code entities
   - `/crg-query callers_of some_function` — should show callers
   - `/crg-impact` — should show blast radius
5. Make edits via aider and verify CRG auto-updates
6. Run `/crg-status` again to confirm graph was updated

### Edge Cases:

- CRG not installed → graceful error message
- Not in a git repo → appropriate error
- Empty repo / no files → handle gracefully
- Large repos → background thread doesn't block aider

---

## Design Decisions

1. **Direct Python API vs MCP subprocess**: Use direct Python API — faster, no serialization overhead, no subprocess management
2. **Slash commands vs replacing repo-map**: Add CRG commands alongside existing repo-map (not replacing it). Users can use both.
3. **Auto-update timing**: Trigger after `auto_commit()` (which fires after aider applies edits and commits). This ensures the graph stays in sync with the actual committed code.
4. **Background updates**: Use daemon threads for auto-update so aider stays responsive
5. **Lazy imports**: Only import CRG when commands are used, so aider starts fast even without CRG installed
