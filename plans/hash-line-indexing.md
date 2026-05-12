# Plan: Hash-Based Line Indexing for EditBlock Format

## Context

aider 当前的 SEARCH/REPLACE 编辑格式依赖纯文本匹配。LLM 看到的文件内容没有行号或标识符，当文件中有重复或相似代码片段时，LLM 容易产生歧义。本方案为每行添加基于内容+位置的短哈希前缀，帮助 LLM 精确定位代码行，同时保持现有文本匹配机制不变。

## Approach

**核心思路**：哈希仅存在于 LLM 视图中，实际匹配仍使用纯文本。

1. 文件展示给 LLM 时，每行加哈希前缀：`a1b2c3 | def foo():`
2. LLM 在 SEARCH 块中包含哈希前缀
3. 解析 SEARCH 块时剥离哈希，用纯文本做匹配
4. REPLACE 块不加哈希（新内容还没有哈希）

**哈希算法**：`SHA256(f"{line_num}:{line_content}")` 截取前 6 个十六进制字符。line_num 为 1-indexed，line_content 为去除尾部换行的行内容。

**兼容性**：如果 LLM 未按指令添加哈希，剥离逻辑不会影响纯文本匹配，完全向后兼容。

## Files to Modify

### 1. `aider/coders/base_coder.py` — 添加哈希前缀到文件内容

**改动点**：`get_files_content()` 方法（约 line 637）和 `get_read_only_files_content()` 方法（约 line 659）

当前代码（line 637-657）：

```python
def get_files_content(self, fnames=None):
    if not fnames:
        fnames = self.abs_fnames
    prompt = ""
    for fname, content in self.get_abs_fnames_content():
        if not is_image_file(fname):
            relative_fname = self.get_rel_fname(fname)
            prompt += "\n"
            prompt += relative_fname
            prompt += f"\n{self.fence[0]}\n"
            prompt += content  # ← 这里需要加哈希前缀
            prompt += f"{self.fence[1]}\n"
    return prompt
```

**改动**：

- 在文件顶部 `import hashlib`
- 新增辅助函数 `compute_line_hash(line_num, line_content)` → 返回 6 字符 hex
- 新增辅助函数 `add_line_hashes(content)` → 为每行添加 `hash | ` 前缀
- 修改 `get_files_content()` 中 `prompt += content` 为 `prompt += add_line_hashes(content)`
- 同样修改 `get_read_only_files_content()`

```python
import hashlib

def compute_line_hash(line_num, line_content):
    """基于行内容和位置计算 6 字符哈希"""
    raw = f"{line_num}:{line_content}"
    return hashlib.sha256(raw.encode()).hexdigest()[:6]

def add_line_hashes(content):
    """为文件内容的每一行添加哈希前缀"""
    lines = content.splitlines(keepends=True)
    result = []
    for i, line in enumerate(lines):
        line_num = i + 1
        line_content = line.rstrip('\n').rstrip('\r\n')
        h = compute_line_hash(line_num, line_content)
        result.append(f"{h} | {line}")
    return "".join(result)
```

### 2. `aider/coders/editblock_coder.py` — 解析时剥离哈希

**改动点**：`find_original_update_blocks()` 函数（约 line 439）中的 `original_text` 处理

当前代码（line 504-508, 528）：

```python
original_text = []
i += 1
while i < len(lines) and not divider_pattern.match(lines[i].strip()):
    original_text.append(lines[i])
    i += 1
...
yield filename, "".join(original_text), "".join(updated_text)
```

**改动**：

- 在文件顶部 `import hashlib`（已有 `import re`）
- 新增函数 `strip_line_hashes(text)` → 剥离每行的 `^[0-9a-f]{6} \| ` 前缀
- 在 yield 之前对 `original_text` 调用 `strip_line_hashes()`

```python
def strip_line_hashes(text):
    """剥离每行的哈希前缀 (如 'a1b2c3 | ')"""
    lines = text.splitlines(keepends=True)
    stripped = []
    for line in lines:
        # 匹配 6 位十六进制 + " | " 前缀
        cleaned = re.sub(r'^[0-9a-f]{6} \| ', '', line)
        stripped.append(cleaned)
    return "".join(stripped)
```

在 `find_original_update_blocks()` 的 yield 处：

```python
yield filename, strip_line_hashes("".join(original_text)), "".join(updated_text)
```

**为什么只剥离 SEARCH（original_text）**：

- REPLACE 块是新代码，LLM 不应添加哈希
- 指令中明确要求 REPLACE 不加哈希

### 3. `aider/coders/editblock_prompts.py` — 更新 LLM 提示

**改动点**：`EditBlockPrompts` 类中的 `system_reminder`（约 line 135）

在 `system_reminder` 中添加关于哈希的说明：

```python
system_reminder = """# *SEARCH/REPLACE block* Rules:
Every *SEARCH/REPLACE block* must use this format:
1. The *FULL* file path alone on a line, verbatim. No bold asterisks, no quotes around it, no escaping of characters, etc.
2. The opening fence and code language, eg: {fence[0]}python
3. The start of search block: <<<<<<< SEARCH
4. A contiguous chunk of lines to search for in the existing src code
5. The dividing line: =======
6. The lines to replace into the src code
7. The end of the replace block: >>>>>>> REPLACE
8. The closing fence: {fence[1]}

Use the *FULL* file path, as shown to you by the user.
{quad_backtick_reminder}

Every source code line shown to you is prefixed with a 6-character hash and " | " separator (e.g., `a1b2c3 | def foo():`).
The hash is computed from the line's content and its position in the file.
When writing *SEARCH* sections, you MUST include the hash prefix on each line exactly as shown in the source code.
The *REPLACE* section should NOT include hash prefixes — write only the new code without hashes.

Every *SEARCH* section must *EXACTLY MATCH* the existing file content, character for character, including all comments, docstrings, etc.
...
```

## Reuse

- `base_coder.py` 中已有的 `get_abs_fnames_content()` 方法用于获取文件内容，无需修改
- `editblock_coder.py` 中已有的 `strip_quoted_wrapping()` 用于去除 fence，无需修改
- 所有下游匹配函数（`perfect_replace`, `replace_most_similar_chunk`, `try_dotdotdots` 等）无需修改，因为哈希在解析阶段就被剥离了

## Steps

- [ ] Step 1: 在 `aider/coders/base_coder.py` 中添加 `import hashlib`，实现 `compute_line_hash()` 和 `add_line_hashes()` 函数
- [ ] Step 2: 修改 `base_coder.py` 中 `get_files_content()` 方法，使用 `add_line_hashes(content)` 替代直接拼接 `content`
- [ ] Step 3: 修改 `base_coder.py` 中 `get_read_only_files_content()` 方法，同样添加哈希前缀
- [ ] Step 4: 在 `aider/coders/editblock_coder.py` 中实现 `strip_line_hashes()` 函数
- [ ] Step 5: 修改 `editblock_coder.py` 中 `find_original_update_blocks()` 函数，在 yield 前剥离哈希
- [ ] Step 6: 修改 `aider/coders/editblock_prompts.py` 中 `system_reminder`，添加哈希使用说明
- [ ] Step 7: 运行现有测试确保不破坏现有功能

## Verification

1. **单元测试**：运行 `pytest tests/basic/test_editblock.py` 确保现有 SEARCH/REPLACE 匹配逻辑不受影响
2. **手动测试**：
   - 启动 aider，`/add` 一个文件，确认 LLM 看到的文件内容包含哈希前缀
   - 发送编辑请求，确认 LLM 在 SEARCH 块中包含哈希
   - 确认编辑能正确应用（哈希被正确剥离后匹配）
3. **兼容性测试**：如果 LLM 未添加哈希的 SEARCH 块，确认仍能正常匹配
4. **回归测试**：运行 `pytest tests/basic/` 确保所有基础测试通过
