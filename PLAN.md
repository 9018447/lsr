# Plan: 添加 `/expand`、`/condense`、`/translate` 斜杠命令

## Context

用户需要在 lsr 中添加三个新的斜杠命令，复用 `/edit` 命令已有的 LaTeX section 选择和 merge-back 机制，但不需要用户手动输入提示词，而是自动注入符合科学写作规范的预设计 prompt。

与 `/edit` 的关键区别：

- `/edit` → 选 section → 创建临时文件 → 用户手动向 LLM 描述编辑需求
- 新命令 → 选 section → **自动注入 prompt** → 直接调用 LLM → 自动 merge back（一站式完成）

## Approach

采用**一站式方案**：命令内部完成 section 选择 → prompt 注入 → 调用 LLM → 自动 merge back，用户只需选 section 即可。

### 核心设计

1. **复用 section 解析逻辑**：提取 `cmd_edit` 中的 LaTeX 结构解析 + 交互选择代码为私有方法 `_parse_and_select_sections(args)`
2. **新增三个命令方法**：`cmd_expand`、`cmd_condense`、`cmd_translate`
3. **每个命令内部流程**：
   - 调用 `_parse_and_select_sections()` 获取选中的 sections
   - 将选中 section 内容 + 预设 prompt 注入为 user message
   - 通过 `_generic_chat_command()` 或直接 `coder.run()` 发送给 LLM
   - LLM 返回编辑结果（使用 SEARCH/REPLACE block 格式，因为 editblock_coder 已支持 LaTeX）
4. **Prompt 设计**（在 `prompts.py` 中新增）

### Prompt 设计（科学写作规范）

#### `/expand` — 扩写

```
你是一位资深的科学论文写作专家。请对以下 LaTeX 章节内容进行扩写。

扩写要求：
1. 保持原有学术风格和术语一致性
2. 补充必要的理论背景、实验细节或数据支撑
3. 添加过渡句和逻辑连接词以增强段落间的连贯性
4. 适当引入相关文献引用（使用 \cite{} 格式），如原文中已有引用则保持一致
5. 扩写后的内容应自然融入原文结构，不改变原有 \section/\subsection 层级
6. 所有 LaTeX 命令和环境的语法必须正确
7. 数学公式（如有）需保持严谨，符号定义须清晰

请直接输出扩写后的完整 LaTeX 代码，使用 SEARCH/REPLACE block 格式。
```

#### `/condense` — 精简

```
你是一位资深的科学论文写作专家。请对以下 LaTeX 章节内容进行精简。

精简要求：
1. 删除冗余表述、重复论述和无关细节，保留核心论点
2. 将冗长句式改写为简洁、直接的学术表述
3. 合并可归纳的段落，消除语义重复
4. 保留所有关键数据、公式、图表引用和文献引用
5. 精简后的内容应保持逻辑完整性和学术严谨性
6. 确保不遗漏重要结论或关键支撑论据
7. 所有 LaTeX 命令和环境的语法必须正确

请直接输出精简后的完整 LaTeX 代码，使用 SEARCH/REPLACE block 格式。
```

#### `/translate` — 翻译（中译英）

```
你是一位资深的科学论文翻译专家，精通中英文双语学术写作。请将以下 LaTeX 章节内容翻译为英文。

翻译要求：
1. 遵循国际学术期刊的英文写作规范（如 IEEE, Elsevier, Springer 等）
2. 使用学术正式用语，避免口语化表达
3. 准确翻译专业术语，首次出现时可保留中文注释
4. 保持所有 LaTeX 命令、环境、标签（\label{}）、引用（\cite{}、\ref{}）不变
5. 数学公式、图表标题、算法伪代码等保持原样
6. 翻译应忠实于原文含义，不增删内容
7. 注意中英文标点差异：英文中不使用中文标点

请直接输出翻译后的完整 LaTeX 代码，使用 SEARCH/REPLACE block 格式。
```

## Files to modify

| 文件              | 修改内容                                                                                              |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| `lsr/commands.py` | 1. 提取 `_parse_and_select_sections()` 共享方法 2. 添加 `cmd_expand`、`cmd_condense`、`cmd_translate` |
| `lsr/prompts.py`  | 添加 `expand_prompt`、`condense_prompt`、`translate_prompt`                                           |

## Reuse

- **Section 解析与选择**：从 `cmd_edit` (lines 2099-2178) 提取复用
- **LLM 调用**：复用 `_generic_chat_command()` (line ~1689) 或 `coder.run()`
- **Editblock coder**：已有的 `editblock_coder` 支持 LaTeX SEARCH/REPLACE block 编辑
- **命令注册机制**：`cmd_xxx` 方法自动注册为 `/xxx` 命令（无需额外注册代码）

## Steps

- [ ] 1. 在 `lsr/prompts.py` 中添加三个预设 prompt 模板（`expand_prompt`、`condense_prompt`、`translate_prompt`）
- [ ] 2. 在 `lsr/commands.py` 中提取 `_parse_and_select_sections(args)` 私有方法，复用 `cmd_edit` 中的 LaTeX 解析 + 交互选择逻辑
- [ ] 3. 实现 `cmd_expand(args)` — 选 section → 注入扩写 prompt → 调用 LLM
- [ ] 4. 实现 `cmd_condense(args)` — 选 section → 注入精简 prompt → 调用 LLM
- [ ] 5. 实现 `cmd_translate(args)` — 选 section → 注入翻译 prompt → 调用 LLM
- [ ] 6. 重构 `cmd_edit` 使其复用 `_parse_and_select_sections()`（消除重复代码）

## Verification

1. 启动 lsr，运行 `/help` 确认三个新命令出现在命令列表中
2. 准备一个包含多个 section 的测试 `.tex` 文件
3. 分别测试：
   - `/expand test.tex` → 选 section → 验证 LLM 扩写了内容且 LaTeX 格式正确
   - `/condense test.tex` → 选 section → 验证内容被精简且关键信息保留
   - `/translate test.tex` → 选 section → 验证内容被翻译为英文且 LaTeX 完整
4. 测试边界情况：不传文件名 → 应显示 usage；传入不存在的文件 → 应报错
