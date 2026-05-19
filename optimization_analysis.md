# EditBlock LaTeX 编辑匹配优化分析

## 问题诊断

当前 `editblock_coder.py` 中的匹配逻辑存在以下问题：

### 1. 模糊匹配被禁用

```python
# 第192-195行 - 被注释掉了！
return
# Try fuzzy matching
res = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)
if res:
    return res
```

### 2. 相似度阈值过高

```python
similarity_thresh = 0.8  # 对LaTeX来说太严格
```

### 3. 缺少LaTeX特殊处理

- LaTeX忽略多余空格（多个空格=一个空格）
- LaTeX注释行（%开头）不影响编译
- LaTeX命令的参数可以跨行

## 优化方案

### 方案1：启用模糊匹配（推荐）

修改 `lsr/coders/editblock_coder.py` 第191行：

```python
# 原代码
return
# Try fuzzy matching
res = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)

# 修改为
# Try fuzzy matching
res = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)
if res:
    return res
return
```

### 方案2：降低相似度阈值

修改第313行：

```python
# 原代码
similarity_thresh = 0.8

# 修改为（针对LaTeX）
similarity_thresh = 0.65  # 更宽松的匹配
```

### 方案3：添加LaTeX专用预处理函数

在 `search_replace.py` 中添加：

```python
def latex_normalize(text):
    """规范化LaTeX文本以提高匹配成功率"""
    lines = text.splitlines(keepends=True)
    normalized = []
    for line in lines:
        # 移除行尾空白
        line = line.rstrip() + "\n"
        # 移除注释（%开头到行尾）
        if not line.lstrip().startswith("%"):
            # 只保留非注释行，或者保留注释但规范化空格
            pass
        # 规范化多个空格为一个（LaTeX特性）
        # 注意：这会破坏代码中的空格，所以只用于匹配，不用于替换
        normalized.append(line)
    return "".join(normalized)


def latex_fuzzy_match(whole_lines, part_lines, replace_lines):
    """LaTeX专用的模糊匹配"""
    # 先尝试忽略注释行的匹配
    # 再尝试忽略空白差异的匹配
    # 最后尝试最相似块匹配
    pass
```

### 方案4：添加LaTeX-aware的匹配策略

在 `search_replace.py` 的 `all_preprocs` 中添加LaTeX专用预处理：

```python
latex_preprocs = [
    (True, False, False),   # strip blank lines
    (True, True, False),    # strip blank + relative indent
    (False, False, False),  # original
]

# 在策略中添加
editblock_strategies = [
    (search_and_replace, all_preprocs),
    (git_cherry_pick_osr_onto_o, all_preprocs),
    (dmp_lines_apply, all_preprocs),
    (latex_fuzzy_match, latex_preprocs),  # 新增
]
```

## 实施建议

### 快速修复（立即可用）

1. 取消注释模糊匹配代码
2. 降低相似度阈值到 0.65-0.7
3. 重新构建项目

### 中期优化（1-2天）

1. 实现 `latex_normalize` 函数
2. 在匹配前对文本进行规范化
3. 添加LaTeX特定的测试用例

### 长期优化（1周）

1. 实现完整的LaTeX-aware匹配器
2. 支持LaTeX命令的语义匹配
3. 添加LaTeX语法验证

## 测试建议

创建测试用例验证优化效果：

```python
def test_latex_matching():
    # 测试1：忽略行尾空白
    whole = "\\begin{equation}\n  x = y\n\\end{equation}\n"
    search = "\\begin{equation}\n  x = y  \n\\end{equation}\n"  # 行尾有多余空格

    # 测试2：忽略注释差异
    whole = "% This is a comment\n\\section{Title}\n"
    search = "\\section{Title}\n"  # 没有注释

    # 测试3：空格规范化
    whole = "\\command{arg1}{arg2}\n"
    search = "\\command{ arg1 }{ arg2 }\n"  # 多余空格
```

## 风险提示

- 降低匹配阈值可能导致错误匹配
- 空格规范化可能破坏代码格式
- 建议添加匹配结果验证

## 参考资料

- diff_match_patch 库文档
- LaTeX语法规范
- 现有测试用例：`tests/` 目录
