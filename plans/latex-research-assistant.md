# 将 Aider 改造为面向 LaTeX 的科研协作助手

## Context

当前 Aider 是面向编程的结对助手，核心围绕代码编辑（13+ 种 edit_format）、代码分析（repomap/tree-sitter）、lint/test 工具链设计。目标是将其改造为面向 LaTeX 科研写作的协作助手，需要：

1. **精简**：移除编程特定的编码器、提示词、工具链
2. **修改**：改造核心模块以支持 LaTeX 工作流
3. **新增**：添加 LaTeX 编辑、编译、文献管理等功能

---

## 一、精简内容（移除编程特定功能）

### 1.1 编码器精简 — `aider/coders/__init__.py`

当前有 **17 个编码器**注册在 `__all__` 中，只需保留 4 个：

| 保留             | edit_format | 理由                                     |
| ---------------- | ----------- | ---------------------------------------- |
| `EditBlockCoder` | `diff`      | 核心编辑机制，搜索/替换块适合 LaTeX 编辑 |
| `AskCoder`       | `ask`       | 纯问答模式，科研讨论需要                 |
| `HelpCoder`      | `help`      | 帮助系统                                 |
| `PlanCoder`      | `plan`      | 论文写作规划                             |

**移除 13 个编码器**（保留文件但从 `__all__` 和 import 中移除）：

| 移除                           | edit_format                                                                         | 文件                                                                  |
| ------------------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `WholeFileCoder`               | `whole`                                                                             | `wholefile_coder.py` + `wholefile_prompts.py`                         |
| `EditBlockFencedCoder`         | `diff-fenced`                                                                       | `editblock_fenced_coder.py` + `editblock_fenced_prompts.py`           |
| `PatchCoder`                   | `patch`                                                                             | `patch_coder.py` + `patch_prompts.py`                                 |
| `UnifiedDiffCoder`             | `udiff`                                                                             | `udiff_coder.py` + `udiff_prompts.py`                                 |
| `UnifiedDiffSimpleCoder`       | `udiff-simple`                                                                      | `udiff_simple.py` + `udiff_simple_prompts.py`                         |
| `HashLineCoder`                | `hashline`                                                                          | `hashline_coder.py` + `hashline_prompts.py`                           |
| `ArchitectCoder`               | `architect`                                                                         | `architect_coder.py` + `architect_prompts.py`                         |
| `EditorEditBlockCoder`         | `editor-diff`                                                                       | `editor_editblock_coder.py` + `editor_editblock_prompts.py`           |
| `EditorWholeFileCoder`         | `editor-whole`                                                                      | `editor_whole_coder.py` + `editor_whole_prompts.py`                   |
| `EditorDiffFencedCoder`        | `editor-diff-fenced`                                                                | `editor_diff_fenced_coder.py` + `editor_diff_fenced_prompts.py`       |
| `ContextCoder`                 | `context`                                                                           | `context_coder.py` + `context_prompts.py`                             |
| `SingleWholeFileFunctionCoder` | `func`                                                                              | `single_wholefile_func_coder.py` + `single_wholefile_func_prompts.py` |
| 以及                           | `wholefile_func_prompts.py`、`editblock_func_prompts.py`、`editblock_func_coder.py` | 辅助文件                                                              |

### 1.2 命令精简 — `aider/commands.py`

**移除/改造的命令**：

| 命令           | 当前功能              | 处理方式                            |
| -------------- | --------------------- | ----------------------------------- |
| `/test`        | 运行测试命令          | **改为** `/compile`（LaTeX 编译）   |
| `/lint`        | 代码检查              | **改为** `/check`（LaTeX 语法检查） |
| `/architect`   | 切换到 architect 模式 | **移除**                            |
| `/context`     | 切换到 context 模式   | **移除**                            |
| `/map`         | 显示代码库映射        | **移除**                            |
| `/map_refresh` | 刷新代码库映射        | **移除**                            |
| `/voice`       | 语音输入              | **可选保留**（口述论文思路有用）    |
| `/paste`       | 粘贴图片              | **保留**（论文图表有用）            |
| `/web`         | 抓取网页              | **改造**（用于抓取论文/参考文献）   |
| `/editor`      | 外部编辑器            | **保留**                            |

**新增命令**：

| 命令         | 功能                           |
| ------------ | ------------------------------ |
| `/compile`   | LaTeX 编译（pdflatex/xelatex） |
| `/preview`   | 打开 PDF 预览                  |
| `/bib`       | 管理参考文献（BibTeX）         |
| `/template`  | 选择/创建论文模板              |
| `/wordcount` | 统计字数                       |

### 1.3 提示词精简

**移除编程特定提示词**：

- `aider/coders/editblock_prompts.py` — 重写：将代码示例替换为 LaTeX 示例
- `aider/coders/ask_prompts.py` — 移除代码分析引用，改为科研写作场景
- `aider/coders/plan_prompts.py` — 已在 CRG 移除计划中处理，进一步改为论文写作规划
- `aider/watch_prompts.py` — 改为 LaTeX 文件监控提示
- `aider/prompts.py` — 检查并移除编程特定内容

### 1.4 工具链精简

| 文件               | 当前功能            | 处理                                          |
| ------------------ | ------------------- | --------------------------------------------- |
| `aider/repomap.py` | 代码库映射（868行） | **禁用**（不删除，但设 `use_repo_map=False`） |
| `aider/linter.py`  | 代码检查（305行）   | **改造**为 LaTeX 语法检查                     |
| `aider/special.py` | 识别重要文件        | **改造**为识别 .tex, .bib, .sty, .cls 文件    |
| `aider/watch.py`   | 文件监控            | **保留**，但修改监控文件类型                  |
| `aider/scrape.py`  | 网页抓取            | **保留**（抓取论文有用）                      |
| `aider/gui.py`     | Streamlit GUI       | **可选移除**或保留                            |
| `aider/voice.py`   | 语音输入            | **保留**（口述有用）                          |

### 1.5 模型配置精简 — `aider/models.py`

- 移除所有模型的 `edit_format = "hashline"` 设置（行 453-610）
- 默认 `edit_format` 改为 `"diff"`（搜索/替换块）
- 移除 `editor_edit_format` 相关逻辑（LaTeX 不需要双模型架构）
- 移除 `use_repo_map = True` 设置

---

## 二、修改内容（改造核心模块）

### 2.1 基础编码器 — `aider/coders/base_coder.py`

**修改点**：

1. **文件识别**：修改文件类型检测，支持 `.tex`, `.bib`, `.sty`, `.cls`, `.dtx`
2. **上下文构建**：移除 repo_map 依赖，改为 LaTeX 文档结构感知（`\input`, `\include`, `\bibliography`）
3. **编辑格式**：确保 `diff` 格式正确处理 LaTeX 内容（特殊字符转义）
4. **提交消息**：改为科研友好的提交消息（如 "Update methods section" 而非 "Fix bug in parser"）

### 2.2 编辑块提示词 — `aider/coders/editblock_prompts.py`

**重写为 LaTeX 版本**：

- 将 "expert software developer" 改为 "expert LaTeX research writer"
- 将 Python 代码示例替换为 LaTeX 示例
- 添加 LaTeX 特定的最佳实践（包管理、交叉引用、公式排版等）
- 移除 shell 命令提示

### 2.3 命令系统 — `aider/commands.py`

**修改点**：

1. 移除 `/architect`, `/context`, `/map`, `/map_refresh` 命令
2. 改造 `/test` → `/compile`
3. 改造 `/lint` → `/check`
4. 修改 `cmd_chat_mode()` 中的 `show_formats`，移除编程特定模式
5. 新增 LaTeX 特定命令

### 2.4 模型设置 — `aider/models.py`

**修改点**：

1. 默认 `edit_format` 从 `"hashline"` 改为 `"diff"`
2. 移除双模型（editor_model）架构的默认配置
3. 为 LaTeX 场景优化 token 限制和上下文窗口

### 2.5 参数配置 — `aider/args.py`

**修改点**：

1. 移除 `--edit-format` 的 `hashline` 选项
2. 移除 `--editor-model` 和 `--editor-edit-format` 参数
3. 新增 LaTeX 特定参数：
   - `--latex-engine` (pdflatex/xelatex/lualatex)
   - `--bib-style` (bibtex/biber)
   - `--template` (论文模板)

### 2.6 Git 集成 — `aider/repo.py`

**保留大部分**，修改：

- 提交消息模板改为科研友好格式
- 添加 `.tex`, `.bib` 到 gitignore 模板

---

## 三、新增内容

### 3.1 LaTeX 编码器 — `aider/coders/latex_coder.py`

新建，基于 `EditBlockCoder` 扩展：

- `edit_format = "diff"` （复用搜索/替换块格式）
- LaTeX 特定的文件解析（识别 `\section`, `\begin{equation}` 等结构）
- 智能上下文（自动包含相关的 `.bib` 和 `.sty` 文件）

### 3.2 LaTeX 提示词 — `aider/coders/latex_prompts.py`

新建，包含：

- LaTeX 写作最佳实践
- 常见论文结构模板
- 数学公式排版指南
- 参考文献管理指南

### 3.3 LaTeX 工具集成 — `aider/latex_tools.py`

新建，包含：

- LaTeX 编译器调用（pdflatex, xelatex, lualatex）
- BibTeX/Biber 处理
- 错误解析和定位
- PDF 预览打开

### 3.4 LaTeX 特殊文件识别 — 修改 `aider/special.py`

添加：

```python
ROOT_IMPORTANT_FILES = [
    # ... 现有文件 ...
    # LaTeX
    "main.tex",
    "main.bib",
    "Makefile",  # LaTeX Makefile
    ".latexmkrc",
    "texmf.cnf",
]
```

### 3.5 LaTeX 文件类型识别 — 修改 `aider/linter.py`

添加 LaTeX 语法检查：

- 检查未闭合的环境
- 检查未定义的引用
- 检查拼写错误

---

## 四、修改的关键文件清单

### 核心修改（必须）

| 文件                                | 修改类型 | 说明                          |
| ----------------------------------- | -------- | ----------------------------- |
| `aider/coders/__init__.py`          | 精简     | 移除 13 个编码器，保留 4 个   |
| `aider/coders/base_coder.py`        | 修改     | LaTeX 文件识别、上下文构建    |
| `aider/coders/editblock_prompts.py` | 重写     | LaTeX 编辑提示词              |
| `aider/commands.py`                 | 修改     | 移除编程命令，新增 LaTeX 命令 |
| `aider/models.py`                   | 修改     | 默认 edit_format、移除双模型  |
| `aider/args.py`                     | 修改     | 移除编程参数，新增 LaTeX 参数 |
| `aider/special.py`                  | 修改     | LaTeX 文件类型识别            |
| `aider/linter.py`                   | 改造     | LaTeX 语法检查                |

### 新增文件

| 文件                            | 说明                                |
| ------------------------------- | ----------------------------------- |
| `aider/coders/latex_coder.py`   | LaTeX 编码器（基于 EditBlockCoder） |
| `aider/coders/latex_prompts.py` | LaTeX 写作提示词                    |
| `aider/latex_tools.py`          | LaTeX 编译和工具集成                |

### 可选精简（不影响核心功能）

| 文件                     | 说明                   |
| ------------------------ | ---------------------- |
| `aider/repomap.py`       | 禁用但不删除           |
| `aider/gui.py`           | 可选移除 Streamlit GUI |
| `aider/watch_prompts.py` | 改为 LaTeX 监控提示    |

---

## 五、实施步骤

### Step 1：精简编码器（低风险，可立即执行）

1. 修改 `aider/coders/__init__.py`，从 `__all__` 和 import 中移除 13 个编码器
2. 测试基本功能正常

### Step 2：重写提示词（核心改造）

1. 重写 `editblock_prompts.py` 为 LaTeX 版本
2. 修改 `ask_prompts.py` 和 `plan_prompts.py`
3. 移除编程特定示例

### Step 3：改造命令系统

1. 移除编程特定命令
2. 新增 LaTeX 命令
3. 修改 `cmd_chat_mode()`

### Step 4：新增 LaTeX 功能

1. 创建 `latex_tools.py`（编译集成）
2. 创建 `latex_coder.py`（可选，如需特定行为）
3. 修改 `special.py` 和 `linter.py`

### Step 5：模型配置优化

1. 修改默认 edit_format
2. 移除双模型架构默认配置
3. 优化 token 设置

---

## 六、验证方案

1. **编译验证**：`python -m py_compile` 检查所有修改文件
2. **导入验证**：`python -c "from aider.coders import Coder"` 确保导入正常
3. **功能测试**：
   - 测试 LaTeX 文件编辑（搜索/替换块格式）
   - 测试 `/compile` 命令
   - 测试 `/bib` 命令
   - 测试 ask/plan 模式
4. **回归测试**：`python -m pytest tests/ -x --timeout=30`
5. **搜索验证**：`grep -r "hashline\|repomap\|tree.sitter" aider/ --include="*.py"` 确保无残留引用

---

## 七、风险评估

| 风险                        | 影响 | 缓解措施                               |
| --------------------------- | ---- | -------------------------------------- |
| 移除编码器后 break 模型配置 | 高   | 确保默认 edit_format 使用保留的 "diff" |
| LaTeX 编译依赖外部工具      | 中   | 检测并提示安装 LaTeX 发行版            |
| 提示词重写后 LLM 行为变化   | 中   | 保留原文件备份，逐步调整               |
| 测试用例依赖移除的功能      | 中   | 更新或跳过相关测试                     |

---

## 八、不动的文件

| 文件/目录         | 原因                             |
| ----------------- | -------------------------------- |
| `aider/repo.py`   | Git 集成核心，保持不变           |
| `aider/io.py`     | 用户界面核心，保持不变           |
| `aider/llm.py`    | LLM 调用核心，保持不变           |
| `aider/models.py` | 只修改默认值，不改结构           |
| `tests/`          | 需要后续更新，但不在本次计划范围 |

---

## 九、执行状态

### 已完成

- [x] Step 1: 精简编码器 - 从 **init**.py 移除 13 个编程编码器
- [x] Step 2: 重写提示词为 LaTeX 科研写作版本
- [x] Step 3: 改造命令系统 - 移除编程命令，新增 LaTeX 命令
- [x] Step 4: 新增 LaTeX 工具集成和新文件
- [x] Step 5: 修改模型配置和参数
- [x] Step 6: 验证所有修改

### 验证结果

```
All imports successful!
Available coders: ['AskCoder', 'EditBlockCoder', 'HelpCoder', 'PlanCoder']
Linter languages: ['python', 'latex']
LaTeX tools: OK
```

### 新增命令

- `/compile` - LaTeX 编译（从 /test 改造）
- `/check` - LaTeX 语法检查（从 /lint 改造）
- `/preview` - 打开 PDF 预览
- `/bib` - 管理参考文献
- `/template` - 选择/创建论文模板
- `/wordcount` - 统计字数
- `/add-template` - 解析 LaTeX 模板

### 新增文件

- `aider/latex_tools.py` - LaTeX 编译和工具集成

### 修改文件

- `aider/coders/__init__.py` - 移除 13 个编码器，保留 4 个
- `aider/coders/editblock_prompts.py` - 重写为 LaTeX 版本
- `aider/coders/ask_prompts.py` - 重写为科研写作场景
- `aider/coders/plan_prompts.py` - 重写为论文写作规划
- `aider/watch_prompts.py` - 更新为 LaTeX 监控提示
- `aider/commands.py` - 移除编程命令，新增 LaTeX 命令
- `aider/models.py` - 默认 edit_format 改为 diff
- `aider/special.py` - 添加 LaTeX 文件识别
- `aider/linter.py` - 添加 LaTeX 语法检查
