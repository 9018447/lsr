# LSR - AI-Powered LaTeX Research Assistant

<p align="center">
<strong>LaTeX 科研写作智能协作助手</strong>
</p>

<p align="center">
基于 <a href="https://github.com/Aider-AI/aider">Aider</a> 二次开发，专注于 LaTeX 科研写作场景。<br>
AI 全程作为写作伙伴提供辅助，所有变更均由研究者主导和确认。
</p>

---

## ✨ 核心特性

- **LaTeX 专属优化** - 原生支持 `.tex`, `.bib`, `.sty`, `.cls`, `.dtx`, `.ins` 文件
- **智能写作助手** - 基于搜索/替换块的精准编辑，科研写作场景优化提示词
- **LaTeX 工具链集成** - 内置编译支持（pdflatex, xelatex, lualatex）及 BibTeX 管理
- **章节级编辑** - 基于 hash 标记的章节追踪、编辑、合并工作流
- **文档分析** - 字数统计、结构分析、引用检查

---

## 🚀 快速开始

### 安装

```bash
# 使用 uv 安装（推荐）
uv pip install git+https://github.com/9018447/lsr.git

# 或使用 pip
pip install git+https://github.com/9018447/lsr.git
```

### 启动

```bash
cd /path/to/your/paper

# 使用 DeepSeek
lsr --model deepseek --api-key deepseek=<your-key>

# 使用 OpenAI
lsr --model gpt-4 --api-key openai=<your-key>

# 使用 Anthropic
lsr --model claude-3-opus --api-key anthropic=<your-key>
```

---

## 📋 斜杠命令（Slash Commands）

### 📝 LaTeX 编辑与编译

| 命令 | 说明 |
|------|------|
| `/compile` | 运行 LaTeX 编译，非零退出码时将输出加入聊天 |
| `/pdflatex` | 使用 pdflatex 引擎编译 |
| `/xelatex` | 使用 xelatex 引擎编译 |
| `/bib` | 管理参考文献 |
| `/bib-pdflatex` | pdflatex → bibtex → pdflatex → pdflatex 完整编译流程 |
| `/bib-xelatex` | xelatex → bibtex → xelatex → xelatex 完整编译流程 |
| `/check` | 检查并修复 LaTeX 语法（环境闭合、引用等） |
| `/preview` | 打开编译后的 PDF 预览 |
| `/template` | 选择或创建 LaTeX 论文模板 |
| `/add-template` | 解析 LaTeX 模板结构，生成内容填充提示词 |
| `/wordcount` | 统计 LaTeX 文件字数 |

### ✂️ 章节编辑工作流

| 命令 | 说明 |
|------|------|
| `/edit` | 基于 hash 标记的 LaTeX 章节编辑（自动识别 `\section` 等结构） |
| `/edit-done` | 将编辑后的章节合并回原文件 |
| `/mark` | 标记章节为已完成（跨会话持久化） |
| `/expand` | 扩展章节，补充更丰富的科研细节 |
| `/condense` | 精简章节，保留核心科学内容 |
| `/translate` | 将中文章节翻译为英文学术风格 |

### 📂 文件管理

| 命令 | 说明 |
|------|------|
| `/add <file>` | 添加文件到聊天会话（可编辑） |
| `/drop <file>` | 从聊天会话移除文件 |
| `/read-only <file>` | 添加只读文件，或将已添加文件设为只读 |
| `/ls` | 列出所有已知文件及其在聊天中的状态 |
| `/open <file>` | 在新终端窗口中用 neovim 打开文件 |

### 💬 聊天模式

| 命令 | 说明 |
|------|------|
| `/ask` | 切换到问答模式（只回答问题，不修改文件） |
| `/plan` | 切换到规划模式（创建结构化写作计划） |
| `/code` | 切换到编辑模式（请求修改 LaTeX 文档） |
| `/ok` | 确认并执行 AI 提议的修改（等同于 `/code Ok, 请继续`） |

### 🔧 模型与配置

| 命令 | 说明 |
|------|------|
| `/model <name>` | 切换 LLM 模型 |
| `/models <keyword>` | 搜索可用模型列表 |
| `/settings` | 显示当前配置 |
| `/think-tokens` | 设置思考 token 数量 |
| `/reasoning-effort` | 设置推理强度 |

### 🛠️ 实用工具

| 命令 | 说明 |
|------|------|
| `/diff` | 显示自上次消息以来的修改 |
| `/undo` | 撤销 lsr 的最后一次 git commit |
| `/commit [msg]` | 提交聊天外的修改（可选提交信息） |
| `/run <cmd>` | 运行 shell 命令（别名: `!`） |
| `/git <args>` | 运行 git 命令（输出不进入聊天） |
| `/tokens` | 报告当前聊天上下文的 token 使用量 |
| `/map` | 显示当前仓库地图 |
| `/copy` | 复制最后一条助手消息到剪贴板 |
| `/copy-context` | 将当前聊天上下文复制为 markdown |
| `/paste` | 从剪贴板粘贴图片/文本到聊天 |
| `/voice` | 录制并转写语音输入 |
| `/web <url>` | 抓取网页内容并转换为 markdown |
| `/editor` | 打开编辑器编写提示词 |
| `/load <file>` | 从文件加载并执行命令 |
| `/save <file>` | 保存当前会话的文件配置到命令文件 |
| `/multiline` | 切换多行模式（交换 Enter 和 Meta+Enter 行为） |
| `/clear` | 清空聊天历史 |
| `/reset` | 清空聊天历史并移除所有文件 |
| `/report` | 在 GitHub 上报告问题 |
| `/help` | 显示帮助信息 |
| `/exit` | 退出程序 |

---

## ⌨️ 快捷键

| 快捷键 | 说明 |
|--------|------|
| `Enter` | 发送消息（多行模式下换行） |
| `Meta+Enter` | 换行（多行模式下发送） |
| `Ctrl+C` | 中断当前操作 |
| `Ctrl+D` | 退出程序 |

---

## 📁 支持的文件类型

| 扩展名 | 说明 |
|--------|------|
| `.tex` | LaTeX 文档 |
| `.bib` | BibTeX 参考文献 |
| `.sty` | LaTeX 样式文件 |
| `.cls` | LaTeX 文档类 |
| `.dtx` | LaTeX 文档化源码 |
| `.ins` | LaTeX 安装文件 |

---

## 🔧 配置

### 环境变量

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export DEEPSEEK_API_KEY=sk-...
```

### 配置文件

在项目根目录创建 `.aider.conf.yml`：

```yaml
model: deepseek
edit-format: diff
latex-engine: pdflatex
auto-compile: true
```

---

## 📚 使用场景示例

```bash
# 学术论文写作
lsr --model gpt-4
> 帮我完善方法部分，添加实验设计的详细描述

# 学位论文
lsr --model deepseek
> /check
> /wordcount
> 帮我检查所有章节的引用是否正确

# 章节编辑工作流
> /edit
# 选择要编辑的章节，AI 会基于 hash 标记追踪修改
> /edit-done
# 合并修改到原文件

# 编译与预览
> /bib-pdflatex
> /preview
```

---

## 🆚 与原版 Aider 的差异

| 功能 | 原版 Aider | LSR |
|------|-----------|-----|
| 定位 | 通用编程助手 | LaTeX 科研写作助手 |
| 文件类型 | 100+ 编程语言 | .tex, .bib, .sty, .cls |
| 编辑格式 | 13+ 种代码格式 | diff（搜索/替换块） |
| 工具链 | lint, test, build | LaTeX 编译, BibTeX |
| 章节编辑 | 无 | `/edit`, `/mark`, `/expand`, `/condense`, `/translate` |
| 提示词 | 代码开发优化 | 学术写作优化 |

---

## 📄 许可证

Apache License 2.0

---

## 🙏 致谢

本项目基于 [Aider](https://github.com/Aider-AI/aider) 二次开发，感谢原项目的优秀基础。
