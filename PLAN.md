# /init 斜杠命令开发计划

## Context

用户需要一个 `/init` 斜杠命令，用于初始化 LaTeX 文件为最小可编译环境。该命令将：
1. 创建新文件或清除现有文件内容
2. 保留最小可编译环境（包含文档类、必要包、文档结构）
3. 每种环境（公式、表格、图）保留一个实例
4. 用占位符代替实际文件（如图片路径）

## Approach

在 `lsr/commands.py` 中添加 `cmd_init` 方法，实现以下功能：

1. **文件处理**：检查文件是否为 `.tex` 文件，如果不存在则创建
2. **内容解析**：提取现有文件的导言区（preamble）信息
3. **生成最小环境**：创建包含以下内容的模板：
   - 文档类声明（\documentclass）
   - 常用包（amsmath, graphicx, booktabs 等）
   - 文档结构（\begin{document}...\end{document}）
   - 一个公式示例（equation 环境）
   - 一个表格示例（table/tabular 环境）
   - 一个图表示例（figure 环境，使用占位符路径）
4. **文件写入**：将生成的内容写入文件

## Files to modify

- `lsr/commands.py`：添加 `cmd_init` 方法及相关辅助方法

## Reuse

- 使用现有的 `parse_quoted_filenames` 函数解析文件参数
- 参考 `cmd_template` 方法的实现模式

## Steps

- [x] Step 1: 在 `Commands` 类中添加 `cmd_init` 方法
- [x] Step 2: 实现文件验证逻辑
- [x] Step 3: 创建最小 LaTeX 模板生成函数
- [x] Step 4: 实现内容清除和模板写入逻辑
- [x] Step 5: 添加错误处理和用户反馈
- [x] Step 6: 测试命令功能
- [x] Step 7: 支持创建不存在的文件

## Verification

1. 创建一个测试 LaTeX 文件，包含复杂内容
2. 运行 `/init test.tex`
3. 验证生成的文件：
   - 包含完整的导言区
   - 包含一个公式、一个表格、一个图示例
   - 使用占位符代替实际文件
   - 可以成功编译（使用 xelatex）
4. 测试创建不存在的文件
5. 测试使用模板目录中的模板

## Implementation Details

### 模板内容结构

```latex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}

\title{Title}
\author{Author}
\date{\today}

\begin{document}
\maketitle

\section{Section Title}

Text content here.

\subsection{Equation Example}

\begin{equation}
    E = mc^2
\label{eq:example}
\end{equation}

\subsection{Table Example}

\begin{table}[htbp]
    \centering
    \caption{Table caption}
    \label{tab:example}
    \begin{tabular}{ccc}
        \toprule
        Column 1 & Column 2 & Column 3 \\
        \midrule
        Data 1 & Data 2 & Data 3 \\
        Data 4 & Data 5 & Data 6 \\
        \bottomrule
    \end{tabular}
\end{table}

\subsection{Figure Example}

\begin{figure}[htbp]
    \centering
    % Replace placeholder.png with your image file
    \includegraphics[width=0.5\textwidth]{placeholder.png}
    \caption{Figure caption}
    \label{fig:example}
\end{figure}

\end{document}
```

### 命令用法

```
/init filename.tex                    # 使用默认模板
/init filename.tex wiley              # 使用 wiley 模板
/init filename.tex template_name      # 使用指定模板
```

### 错误处理

- 文件不是 .tex 文件：提示错误
- 模板不存在：提示错误
- 文件写入失败：提示错误
