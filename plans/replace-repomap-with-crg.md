# Plan: 替换 aider RepoMap，使用 code-review-graph 的 graph.db

## Context

aider 的 `RepoMap`（`aider/repomap.py`）使用 tree-sitter 提取代码标签，用 NetworkX PageRank 排序文件，再渲染树形上下文。

现在要用 code-review-graph 的 `graph.db`（SQLite）替代它。用户会单独安装 CRG CLI 并手动 `code-review-graph build` 生成 `.code-review-graph/graph.db`。我们只需读取这个数据库来生成 repo map。

## 方案

直接读取 `.code-review-graph/graph.db` 的 SQLite 数据库（用内置 `sqlite3`，不引入额外依赖）。用 graph 中的边关系（CALLS、IMPORTS_FROM、INHERITS 等）来排序文件，替代原来的 PageRank。渲染仍使用 `grep_ast.TreeContext`。

---

## graph.db Schema（已确认）

```sql
-- nodes 表：文件、函数、类、测试等
nodes(id, kind, name, qualified_name, file_path, line_start, line_end,
      language, parent_name, params, return_type, modifiers, is_test, file_hash, extra, updated_at)

-- edges 表：调用、导入、继承等关系
edges(id, kind, source_qualified, target_qualified, file_path, line, extra, confidence, confidence_tier, updated_at)

-- kind 枚举：File, Class, Function, Type, Test
-- edge kind 枚举：CALLS, IMPORTS_FROM, INHERITS, IMPLEMENTS, CONTAINS, TESTED_BY, DEPENDS_ON, REFERENCES
```

数据库路径：`<repo_root>/.code-review-graph/graph.db`

---

## Files to Modify

| File                         | Action                                    |
| ---------------------------- | ----------------------------------------- |
| `aider/crg_repomap.py`       | **新建** — `CrgRepoMap` 类，读取 graph.db |
| `aider/coders/base_coder.py` | **修改** — 用 `CrgRepoMap` 替换 `RepoMap` |

---

## Reuse

- `grep_ast.TreeContext` — 已有依赖，用于渲染树形代码视图
- `aider.repomap.find_src_files()` — 如果需要列出源文件
- `aider.coders.base_coder.Coder.get_repo_map()` — 接口不变，只换内部实现
- `main_model.token_count()` — token 计数不变

---

## 实现步骤

### Step 1: 新建 `aider/crg_repomap.py`

```python
"""Code-Review-Graph based repo map — reads .code-review-graph/graph.db."""
import os
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from grep_ast import TreeContext


class CrgRepoMap:
    """Generate repo map from code-review-graph's SQLite database."""

    def __init__(self, map_tokens, root, main_model, io, repo_content_prefix,
                 verbose=False, max_context_window=None,
                 map_mul_no_files=8, refresh="auto"):
        self.map_tokens = map_tokens
        self.root = root
        self.main_model = main_model
        self.io = io
        self.repo_content_prefix = repo_content_prefix
        self.verbose = verbose
        self.max_context_window = max_context_window
        self.map_mul_no_files = map_mul_no_files

        # 定位 graph.db
        self.db_path = Path(root) / ".code-review-graph" / "graph.db"
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"graph.db not found at {self.db_path}. "
                f"Run 'code-review-graph build' first."
            )
        # Cache for ranked results
        self._cache = {}
        self._last_cache_time = 0

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def token_count(self, text):
        """Estimate token count via main_model."""
        # 复用 legacy 的采样策略
        len_text = len(text)
        if len_text < 200:
            return self.main_model.token_count(text)
        lines = text.splitlines(keepends=True)
        step = len(lines) // 100 or 1
        sample = "".join(lines[::step])
        return int(self.main_model.token_count(sample) / len(sample) * len_text)

    def get_repo_map(self, chat_files, other_files,
                     mentioned_fnames=None, mentioned_idents=None,
                     force_refresh=False):
        """Generate a repo map string from the graph database.

        逻辑：
        1. 从 graph.db 中找出 chat_files 对应的节点
        2. 通过边关系（CALLS, IMPORTS_FROM, INHERITS 等）找到相关文件
        3. 按边权重 + 提及信号排序文件
        4. 对 top 文件用 TreeContext 渲染代码片段
        5. 二分搜索适配 token 预算
        """
        if self.map_tokens <= 0:
            return None
        if not other_files:
            return None

        mentioned_fnames = mentioned_fnames or set()
        mentioned_idents = mentioned_idents or set()

        max_map_tokens = self.map_tokens
        # 没有 chat files 时，给更大视野
        padding = 4096
        if not chat_files and self.max_context_window:
            target = min(
                int(max_map_tokens * self.map_mul_no_files),
                self.max_context_window - padding,
            )
            if target > 0:
                max_map_tokens = target

        try:
            ranked_files = self._rank_files(
                chat_files, other_files, mentioned_fnames, mentioned_idents
            )
        except Exception as e:
            if self.verbose:
                self.io.tool_warning(f"CRG repo map error: {e}")
            return None

        if not ranked_files:
            return None

        # 渲染树形视图，二分搜索适配 token 预算
        result = self._render_ranked_files(ranked_files, max_map_tokens, chat_files)
        if not result:
            return None

        if self.verbose:
            num_tokens = self.token_count(result)
            self.io.tool_output(f"CRG Repo-map: {num_tokens / 1024:.1f} k-tokens")

        # 添加前缀
        if chat_files:
            other = "other "
        else:
            other = ""
        if self.repo_content_prefix:
            repo_content = self.repo_content_prefix.format(other=other)
        else:
            repo_content = ""
        repo_content += result
        return repo_content

    def _rank_files(self, chat_files, other_files,
                    mentioned_fnames, mentioned_idents):
        """Rank other_files by relevance to chat_files via graph edges."""
        conn = self._connect()
        try:
            chat_abs = set(str(Path(f).resolve()) for f in chat_files)
            other_abs = set(str(Path(f).resolve()) for f in other_files)
            all_abs = chat_abs | other_abs

            # 1. 找到 chat_files 中所有节点的 qualified_name
            chat_qns = set()
            for f in chat_abs:
                rows = conn.execute(
                    "SELECT qualified_name FROM nodes WHERE file_path = ?",
                    (f,)
                ).fetchall()
                chat_qns.update(r[0] for r in rows)

            # 2. 通过边关系找到关联文件，计算权重
            file_scores = defaultdict(float)

            # 向外边：chat 中的节点调用/导入的文件
            for qn in chat_qns:
                rows = conn.execute(
                    "SELECT target_qualified, kind FROM edges WHERE source_qualified = ?",
                    (qn,)
                ).fetchall()
                for r in rows:
                    target_qn = r[0]
                    kind = r[1]
                    weight = _edge_weight(kind)
                    # 找到 target 所在文件
                    tfile = _qn_to_file(target_qn, conn)
                    if tfile and tfile in other_abs:
                        file_scores[tfile] += weight

            # 向内边：调用/导入 chat 中节点的文件
            for qn in chat_qns:
                rows = conn.execute(
                    "SELECT source_qualified, kind FROM edges WHERE target_qualified = ?",
                    (qn,)
                ).fetchall()
                for r in rows:
                    source_qn = r[0]
                    kind = r[1]
                    weight = _edge_weight(kind)
                    sfile = _qn_to_file(source_qn, conn)
                    if sfile and sfile in other_abs:
                        file_scores[sfile] += weight * 0.8  # 向内略低于向外

            # 3. 提及信号加分
            for fname in mentioned_fnames:
                abs_fname = str(Path(self.root) / fname)
                abs_fname = str(Path(abs_fname).resolve())
                if abs_fname in other_abs:
                    file_scores[abs_fname] += 100

            # mentioned_idents：在 nodes 表中搜索
            if mentioned_idents:
                placeholders = " OR ".join(
                    "name = ?" for _ in mentioned_idents
                )
                rows = conn.execute(
                    f"SELECT DISTINCT file_path FROM nodes WHERE {placeholders}",
                    list(mentioned_idents),
                ).fetchall()
                for r in rows:
                    fp = r[0]
                    if fp in other_abs:
                        file_scores[fp] += 50

            # 4. 没有边连接的文件给低分保底
            for f in other_abs:
                if f not in file_scores:
                    file_scores[f] = 0.01

            # 排序
            ranked = sorted(file_scores.items(), key=lambda x: -x[1])
            return [f for f, _ in ranked]
        finally:
            conn.close()

    def _render_ranked_files(self, ranked_files, max_map_tokens, chat_files):
        """Render tree-context view of top-ranked files, fitting token budget."""
        chat_abs = set(str(Path(f).resolve()) for f in chat_files)

        # 获取每个文件的节点（函数/类）及其行号
        conn = self._connect()
        try:
            file_lois = {}  # file_path -> list of (line_start, node_name)
            for f in ranked_files:
                rows = conn.execute(
                    "SELECT name, kind, line_start, line_end FROM nodes "
                    "WHERE file_path = ? AND kind IN ('Function', 'Class', 'Type', 'Test') "
                    "ORDER BY line_start",
                    (f,)
                ).fetchall()
                file_lois[f] = [(r[2], r[0], r[1]) for r in rows if r[2] is not None]
        finally:
            conn.close()

        # 二分搜索：找最多能放多少文件
        num_files = len(ranked_files)
        lower_bound = 0
        upper_bound = num_files
        best_tree = None
        best_tree_tokens = 0

        while lower_bound <= upper_bound:
            middle = (lower_bound + upper_bound) // 2
            if middle == 0:
                lower_bound = 1
                continue

            tree = self._render_files(ranked_files[:middle], file_lois, chat_abs)
            num_tokens = self.token_count(tree)

            pct_err = abs(num_tokens - max_map_tokens) / max_map_tokens
            ok_err = 0.15
            if (num_tokens <= max_map_tokens and num_tokens > best_tree_tokens) or pct_err < ok_err:
                best_tree = tree
                best_tree_tokens = num_tokens
                if pct_err < ok_err:
                    break

            if num_tokens < max_map_tokens:
                lower_bound = middle + 1
            else:
                upper_bound = middle - 1

        return best_tree

    def _render_files(self, files, file_lois, chat_abs):
        """Render a set of files using TreeContext."""
        output = ""
        for abs_fname in files:
            if abs_fname in chat_abs:
                continue

            rel_fname = os.path.relpath(abs_fname, self.root)
            lois = file_lois.get(abs_fname, [])

            if not lois:
                # 没有函数/类节点的文件，只显示文件名
                output += f"\n{rel_fname}\n"
                continue

            code = self.io.read_text(abs_fname)
            if not code:
                continue
            if not code.endswith("\n"):
                code += "\n"

            loi_lines = [line for line, _, _ in lois]

            try:
                context = TreeContext(
                    rel_fname, code,
                    color=False, line_number=False,
                    child_context=False, last_line=False,
                    margin=0, mark_lois=False, loi_pad=0,
                    show_top_of_file_parent_scope=False,
                )
                context.lines_of_interest = set()
                context.add_lines_of_interest(loi_lines)
                context.add_context()
                rendered = context.format()
            except Exception:
                rendered = "\n".join(
                    f" {line}: {code.splitlines()[line-1]}"
                    for line in loi_lines
                    if 0 < line <= len(code.splitlines())
                )

            output += f"\n{rel_fname}:\n{rendered}"

        # 截断超长行（防止 minified code）
        output = "\n".join(line[:100] for line in output.splitlines()) + "\n"
        return output


def _edge_weight(kind):
    """Edge kind -> importance weight."""
    weights = {
        "CALLS": 5.0,
        "IMPORTS_FROM": 4.0,
        "INHERITS": 3.0,
        "IMPLEMENTS": 3.0,
        "CONTAINS": 2.0,
        "TESTED_BY": 2.0,
        "DEPENDS_ON": 1.5,
        "REFERENCES": 1.0,
    }
    return weights.get(kind, 1.0)


def _qn_to_file(qualified_name, conn):
    """Extract the file_path from a qualified_name (format: 'file.py::Class.method')."""
    if "::" in qualified_name:
        file_part = qualified_name.split("::", 1)[0]
    else:
        file_part = qualified_name

    # 验证：直接查 nodes 表获取 file_path
    row = conn.execute(
        "SELECT file_path FROM nodes WHERE qualified_name = ? LIMIT 1",
        (qualified_name,)
    ).fetchone()
    if row:
        return row[0]

    # fallback：用 qualified_name 的文件部分
    if file_part and os.path.isabs(file_part):
        return file_part
    return None
```

### Step 2: 修改 `aider/coders/base_coder.py`

**改动 1：替换 import**

```python
# 原来：
from aider.repomap import RepoMap

# 改为：
try:
    from aider.crg_repomap import CrgRepoMap
except ImportError:
    CrgRepoMap = None
from aider.repomap import RepoMap  # 保留作为 fallback
```

**改动 2：替换 RepoMap 实例化**（约 line 534-545）

```python
# 原来：
if use_repo_map and self.repo and has_map_prompt:
    self.repo_map = RepoMap(
        map_tokens, self.root, self.main_model, io,
        self.gpt_prompts.repo_content_prefix, self.verbose,
        max_inp_tokens, map_mul_no_files=map_mul_no_files,
        refresh=map_refresh,
    )

# 改为：
if use_repo_map and self.repo and has_map_prompt:
    # 优先使用 CRG graph.db
    if CrgRepoMap is not None:
        try:
            self.repo_map = CrgRepoMap(
                map_tokens, self.root, self.main_model, io,
                self.gpt_prompts.repo_content_prefix, self.verbose,
                max_inp_tokens, map_mul_no_files=map_mul_no_files,
                refresh=map_refresh,
            )
        except FileNotFoundError:
            self.repo_map = RepoMap(
                map_tokens, self.root, self.main_model, io,
                self.gpt_prompts.repo_content_prefix, self.verbose,
                max_inp_tokens, map_mul_no_files=map_mul_no_files,
                refresh=map_refresh,
            )
    else:
        self.repo_map = RepoMap(
            map_tokens, self.root, self.main_model, io,
            self.gpt_prompts.repo_content_prefix, self.verbose,
            max_inp_tokens, map_mul_no_files=map_mul_no_files,
            refresh=map_refresh,
        )
```

**注意**：如果 graph.db 不存在（`FileNotFoundError`），自动 fallback 到 legacy `RepoMap`。其余代码（`get_repo_map()`, `get_repo_messages()` 等）完全不需要改动，因为 `CrgRepoMap` 实现了相同的接口。

---

## Verification

1. 在一个项目中运行 `code-review-graph build`
2. 确认 `.code-review-graph/graph.db` 存在
3. 运行 aider，观察 announcements 中是否显示 "Repo-map: using CRG backend"
4. 使用 `/map` 命令查看 repo map
5. 对比 CRG 和 legacy 的输出质量
6. 测试 graph.db 不存在时的 fallback 行为
