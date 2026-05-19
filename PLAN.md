# Plan: 彻底删除 aider 中的 CRG (code-review-graph) 工具

## Context

用户在 aider 中自行开发了 CRG (code-review-graph) 工具集，包括：

- 3 个核心 Python 模块（`crg_common.py`, `crg_tool_adapter.py`, `crg_toolkit.py`）
- 在 `commands.py` 中注册的 `/crg` 和 `/crg_setup` 命令
- 在 `base_coder.py` 中的 LLM 自动调用集成
- 在多个 prompt 模板中注入的 CRG 使用指令
- 配套的测试、wiki、plan 文件和 Gemini hooks

现在需要彻底移除所有 CRG 相关代码，恢复 aider 到未集成 CRG 的状态，**不影响其他功能**。

---

## 一、删除整个文件（11 个文件 + 1 个目录）

### 核心模块（3 个）

| 文件                        | 说明                             |
| --------------------------- | -------------------------------- |
| `aider/crg_common.py`       | 数据类 + SQLite loader（395 行） |
| `aider/crg_tool_adapter.py` | LLM 工作流适配器（355 行）       |
| `aider/crg_toolkit.py`      | CLI 工具包（652 行）             |

### 测试（1 个）

| 文件                              | 说明                           |
| --------------------------------- | ------------------------------ |
| `tests/basic/test_crg_toolkit.py` | CRG 搜索/模糊匹配/自动刷新测试 |

### Wiki 文档（3 个）

| 文件                           | 说明                     |
| ------------------------------ | ------------------------ |
| `wiki/community_aider-crg.md`  | CRG 适配器社区文档       |
| `wiki/community_aider-node.md` | CRG 节点社区文档         |
| `wiki/community_aider-cmd.md`  | CRG toolkit 命令社区文档 |

### 计划文档（1 个）

| 文件                                | 说明                           |
| ----------------------------------- | ------------------------------ |
| `plans/replace-repomap-with-crg.md` | 用 CRG 替换 RepoMap 的计划文档 |

### Gemini 配置（2 个文件 + 1 个目录）

| 文件                                 | 说明                               |
| ------------------------------------ | ---------------------------------- |
| `.gemini/hooks/crg-session-start.sh` | Gemini CLI session start hook      |
| `.gemini/hooks/crg-update.sh`        | Gemini CLI 文件变更后自动更新 hook |
| `.code-review-graph/`                | graph.db 数据库目录（整个目录）    |

### Gemini settings.json 需清空 hooks 配置

| 文件                    | 说明                                     |
| ----------------------- | ---------------------------------------- |
| `.gemini/settings.json` | 移除 CRG 相关的 mcpServers 和 hooks 配置 |

---

## 二、修改文件（6 个文件）

### 1. `aider/commands.py`

- **删除 `cmd_crg()` 方法**（第 1067-1092 行）：`/crg` 命令实现
- **删除 `cmd_crg_setup()` 方法**（第 1094-1112 行）：`/crg_setup` 命令实现
- **修改 `cmd_plan()` 描述**（第 1296 行）：将 `"Explore the codebase with CRG tools and create a structured plan."` 改为 `"Create a structured plan before coding."`
- **修改模式说明**（第 163 行）：将 `"Explore the codebase with CRG tools and create a structured plan before coding."` 改为 `"Create a structured plan before coding."`

### 2. `aider/coders/base_coder.py`

- **删除 CRG 初始化代码**（第 657-670 行）：移除 `ensure_graph_db`、`refresh_graph_db`、`crg_tool_enabled` 初始化
- **删除自动执行 CRG 工具的代码**（第 1113-1120 行）：移除 `execute_crg_tools` 调用和 `reflected_message` 设置
- **删除 CRG prompt 注入代码**（第 1443-1447 行）：移除 `get_crg_prompt_for_mode` 调用

### 3. `aider/coders/plan_prompts.py`

- **重写整个 prompt**：移除所有 CRG 相关内容
  - 删除模块文档中的 CRG 引用
  - 删除 Step 2 "Explore with CRG Tools" 及 `<crg_tool>` 标签示例
  - 删除 Step 3 中 CRG 分析的引用
  - 删除所有 `<crg_tool subcommand=...>` 标签说明
  - 保留 plan 模式的核心工作流结构

### 4. `aider/coders/plan_coder.py`

- **修改文档字符串**（第 4 行）：将 `"In plan mode the LLM explores the codebase with CRG tools and produces"` 改为 `"In plan mode the LLM explores the codebase and produces"`

### 5. `aider/coders/ask_prompts.py`

- **删除 CRG 引用**（第 11 行）：删除 `"When analyzing code relationships, architecture, or change impact, proactively use the CRG toolkit to provide evidence-based answers."` 这一行

### 6. `aider/coders/editblock_prompts.py`

- **删除 CRG 引用**（第 24 行）：将 `"If a plan has been previously discussed, follow it closely. Use CRG tools if you need to verify call chains or impact during implementation."` 改为 `"If a plan has been previously discussed, follow it closely."`

---

## 三、不动的文件（安全不动）

| 文件/目录                  | 原因                                       |
| -------------------------- | ------------------------------------------ |
| `aider for latex/`         | 这是独立的副本，不属于主项目               |
| `.pi-lens/cache/`          | 自动缓存，不影响功能                       |
| `wiki/index.md`            | 仅索引引用，删掉被索引的文件后索引自然失效 |
| `pyproject.toml`           | 不含 CRG 引用                              |
| `aider/__init__.py`        | 不含 CRG 引用                              |
| `aider/coders/__init__.py` | 仅引入 PlanCoder，不涉及 CRG               |

---

## 四、执行顺序

**Step 1** — 删除核心模块文件

```
rm aider/crg_common.py aider/crg_tool_adapter.py aider/crg_toolkit.py
```

**Step 2** — 删除测试、文档、计划文件

```
rm tests/basic/test_crg_toolkit.py
rm wiki/community_aider-crg.md wiki/community_aider-node.md wiki/community_aider-cmd.md
rm plans/replace-repomap-with-crg.md
```

**Step 3** — 删除 Gemini 配置和数据目录

```
rm .gemini/hooks/crg-session-start.sh .gemini/hooks/crg-update.sh
rm -rf .code-review-graph/
```

编辑 `.gemini/settings.json`，移除 CRG 相关的 hooks 配置（保留文件但清空 hooks 部分）

**Step 4** — 修改 `aider/commands.py`

- 删除 `cmd_crg` 和 `cmd_crg_setup` 两个方法
- 修改 plan 模式的描述文本

**Step 5** — 修改 `aider/coders/base_coder.py`

- 删除 3 处 CRG 相关代码块

**Step 6** — 修改 prompt 模板文件

- `aider/coders/plan_prompts.py` — 重写，移除所有 CRG 内容
- `aider/coders/ask_prompts.py` — 删除 CRG 引用行
- `aider/coders/editblock_prompts.py` — 删除 CRG 引用
- `aider/coders/plan_coder.py` — 修改文档字符串

**Step 7** — 清理 Gemini settings

- 编辑 `.gemini/settings.json`，移除 `code-review-graph` MCP server 和 CRG hooks

---

## 五、验证

1. **语法检查**：`python -m py_compile aider/commands.py aider/coders/base_coder.py aider/coders/plan_prompts.py aider/coders/ask_prompts.py aider/coders/editblock_prompts.py aider/coders/plan_coder.py`
2. **运行测试**：`python -m pytest tests/ -x --timeout=30` 确保没有因 CRG 移除导致的测试失败
3. **搜索验证**：`grep -r "crg\|CRG\|code-review-graph\|graph\.db" aider/ --include="*.py"` 确保 aider Python 源码中不再有任何 CRG 引用
4. **导入验证**：`python -c "from aider.coder import Coder"` 确保导入链正常
