# Troubleshooting: SEARCH/REPLACE 匹配失败

## 问题描述

当编辑 LaTeX 文件时，SEARCH/REPLACE 块总是匹配失败，尤其是：
- 面对大范围内容但只修改小范围内容时（如仅修改 \cite{} 引用）
- 错误提示：`SearchReplaceNoExactMatch: This SEARCH block failed to exactly match lines`

## 根本原因

LLM 生成 SEARCH 块时，基于其看到的渲染后文本，可能与实际 LaTeX 源文件有以下差异：

### 1. LaTeX 转义字符丢失
- 文件: `\%` → LLM 搜索: `%`
- 文件: `\$` → LLM 搜索: `$`

### 2. Unicode 空白字符变体
- 文件: U+202F (narrow no-break space) → LLM 搜索: U+0020 (regular space)

### 3. 原有匹配流程不足
`replace_ignoring_line_breaks` 的 `normalize_whitespace` 只统一空白，不处理 LaTeX 转义。

## 修复内容

### 文件: `lsr/coders/editblock_coder.py`

#### 新增函数
- `normalize_latex_escapes(text)` — 将 `\%` → `%`, `\$` → `$` 等，用于模糊比较
- `normalize_for_matching(text)` — 组合 LaTeX 归一化 + 空白归一化

#### 修改函数
- `replace_ignoring_line_breaks()`:
  - 使用 `normalize_for_matching` 替代 `normalize_whitespace`
  - `startswith` → `in`（子串匹配），支持行内匹配
  - 删除 `return None` 后的死代码
  - 增加多行块长度扫描逻辑

### 测试: `tests/test_latex_matching.py`
- 16 个测试用例全部通过
- 覆盖: LaTeX 转义归一化、组合归一化、行内匹配、完整管道、端到端

## 验证

```bash
cd /home/smh/lsr-dev && python -m pytest tests/test_latex_matching.py -v
# 16 passed in 0.35s
```
