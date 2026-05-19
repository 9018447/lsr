# AI-Powered LaTeX Research Assistant

<p align="center">
    <strong>LaTeX 科研写作智能协作助手</strong>
</p>

<p align="center">
区别于通用编程助手，本工具专注于 LaTeX 科研写作场景，AI 全程作为写作伙伴提供辅助能力，所有变更均由研究者主导和确认。
</p>

---

## ✨ 核心特性

### 📝 LaTeX 专属优化

- 原生支持 .tex, .bib, .sty, .cls 文件编辑
- LaTeX 语法检查（环境闭合、引用检查）
- 智能识别文档结构（章节、公式、图表、参考文献）

### 🤖 智能写作助手

- 基于搜索/替换块的精准编辑
- 支持所有主流 LLM（OpenAI, Anthropic, DeepSeek 等）
- 科研写作场景优化的提示词

### 🔧 LaTeX 工具集成

- 内置 LaTeX 编译支持（pdflatex, xelatex, lualatex）
- BibTeX 参考文献管理
- 论文模板系统

### 📊 文档分析

- 字数统计
- 结构分析（章节、图表、公式计数）
- 参考文献引用检查

---

## 🚀 快速开始

### 安装

```bash
# 使用 uv 安装（推荐）
uv pip install git+https://github.com/your-username/lsr.git

# 或使用 pip
pip install git+https://github.com/your-username/lsr.git
```

### 启动

```bash
# 进入你的 LaTeX 项目目录
cd /path/to/your/paper

# 启动助手（以 DeepSeek 为例）
lsr --model deepseek --api-key deepseek=<your-key>

# 或使用 OpenAI
lsr --model gpt-4 --api-key openai=<your-key>
```

### 基础使用

1. **编辑 LaTeX 文档**

```
> 添加一个关于研究方法的章节
```

2. **添加数学公式**

```
> 在方法部分添加回归模型的数学公式
```

3. **管理参考文献**

```
> 在引言中添加对 Smith 2023 的引用
```

4. **检查语法**

```
> /check
```

5. **编译文档**

```
> /compile
```

6. **预览 PDF**

```
> /preview
```

---

## 📋 命令列表

| 命令            | 说明                |
| --------------- | ------------------- |
| `/compile`      | 编译 LaTeX 文档     |
| `/check`        | 检查 LaTeX 语法     |
| `/preview`      | 打开 PDF 预览       |
| `/bib`          | 管理参考文献        |
| `/template`     | 选择/创建论文模板   |
| `/wordcount`    | 统计字数            |
| `/add-template` | 解析 LaTeX 模板结构 |
| `/add <file>`   | 添加文件到会话      |
| `/drop <file>`  | 从会话中移除文件    |
| `/undo`         | 撤销上一次修改      |
| `/diff`         | 显示当前修改        |
| `/run <cmd>`    | 运行 shell 命令     |
| `/ask`          | 切换到问答模式      |
| `/plan`         | 切换到写作规划模式  |
| `/code`         | 切换到编辑模式      |

---

## 📁 支持的文件类型

| 扩展名 | 说明             |
| ------ | ---------------- |
| `.tex` | LaTeX 文档       |
| `.bib` | BibTeX 参考文献  |
| `.sty` | LaTeX 样式文件   |
| `.cls` | LaTeX 文档类     |
| `.dtx` | LaTeX 文档化源码 |
| `.ins` | LaTeX 安装文件   |

---

## 🔧 配置

### 环境变量

```bash
# OpenAI API Key
export OPENAI_API_KEY=sk-...

# Anthropic API Key
export ANTHROPIC_API_KEY=sk-ant-...

# DeepSeek API Key
export DEEPSEEK_API_KEY=sk-...
```

### 配置文件

在项目根目录创建 `.aider.conf.yml`：

```yaml
# 默认模型
model: deepseek

# 编辑格式
edit-format: diff

# LaTeX 编译引擎
latex-engine: pdflatex

# 自动编译
auto-compile: true
```

---

## 📚 使用场景

### 学术论文写作

```bash
lsr --model gpt-4
> 帮我完善方法部分，添加实验设计的详细描述
```

### 学位论文

```bash
lsr --model deepseek
> 帮我检查所有章节的引用是否正确
```

### 会议论文

```bash
lsr --model claude-3-opus
> 根据会议模板调整论文格式
```

### 文献综述

```bash
latex-assist --model gpt-4
> 帮我整理参考文献，按主题分类
```

---

## 🆚 与原版 Aider 的差异

| 功能     | 原版 Aider        | LaTeX Research Assistant |
| -------- | ----------------- | ------------------------ |
| 定位     | 通用编程助手      | LaTeX 科研写作助手       |
| 文件类型 | 100+ 编程语言     | .tex, .bib, .sty, .cls   |
| 编辑格式 | 13+ 种代码格式    | diff（搜索/替换块）      |
| 工具链   | lint, test, build | LaTeX 编译, BibTeX       |
| 提示词   | 代码开发优化      | 学术写作优化             |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

Apache License 2.0

---

## 🙏 致谢

本项目基于 [Aider](https://github.com/Aider-AI/aider) 二次开发，感谢原项目的优秀基础。
