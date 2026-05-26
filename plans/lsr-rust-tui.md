# LSR Rust TUI 重写计划

## Context

LSR (LaTeX Research Assistant) 是一个基于 Python 的 AI 驱动 LaTeX 科研写作助手，当前约 21,000 行 Python 代码。用户希望：

1. **设计 TUI 界面** — 使用 ratatui 构建现代化终端用户界面
2. **1:1 转换为 Rust** — 尽可能将 Python 源码结构映射到 Rust

当前 Python 架构：
- `lsr/main.py` (1,160 行) — 入口和初始化
- `lsr/io.py` (1,251 行) — 用户交互（prompt_toolkit + rich）
- `lsr/commands.py` (4,575 行) — 命令系统（50+ 斜杠命令）
- `lsr/coders/base_coder.py` (2,648 行) — 核心编码器逻辑
- `lsr/coders/editblock_coder.py` (1,145 行) — 搜索/替换编辑
- `lsr/models.py` (1,378 行) — LLM 模型管理
- `lsr/repo.py` (667 行) — Git 集成
- `lsr/repomap.py` (867 行) — 代码库映射
- `lsr/latex_tools.py` (422 行) — LaTeX 编译工具
- 其他辅助模块 (~3,000 行)

---

## 一、TUI 界面设计

### 1.1 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│ LSR v0.1.0 │ Model: claude-sonnet-4 │ Files: 3 │ Git: main │ <- 状态栏 (Status Bar)
├──────────────────────────────────┬──────────────────────────┤
│                                  │                          │
│                                  │    文件树 / Repo Map     │ <- 侧边栏
│        聊天区域                  │    (File Tree Panel)     │
│   (Chat Area - Markdown)        │                          │
│                                  │    .tex                  │
│   [User] 请帮我修改摘要...       │    ├── main.tex          │
│                                  │    ├── sections/         │
│   [Assistant] 我来帮你修改...     │    │   ├── intro.tex     │
│                                  │    │   └── methods.tex   │
│                                  │    └── refs.bib          │
│                                  │                          │
├──────────────────────────────────┴──────────────────────────┤
│ > /compile main.tex                                         │ <- 输入栏 (Input Bar)
│ [Tab: 命令补全] [Ctrl+L: 清屏] [Ctrl+O: 文件选择]           │ <- 快捷键提示
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

| 组件 | Widget 类型 | 功能 |
|------|-------------|------|
| **StatusBar** | `Paragraph` + `Line` | 显示模型、文件数、Git 分支、token 使用 |
| **ChatArea** | `Paragraph` (滚动) | Markdown 渲染的聊天内容 |
| **InputBar** | 自定义 Widget | 命令输入，支持补全、历史 |
| **FileTree** | `List` (stateful) | 项目文件树，可选择添加文件 |
| **CommandPalette** | `List` (弹出) | 斜杠命令快速选择 |
| **DiffView** | `Table` | 编辑差异对比视图 |
| **CompileOutput** | `Paragraph` (滚动) | LaTeX 编译输出 |
| **ProgressBar** | `Gauge` | LLM 响应进度 / 编译进度 |

### 1.3 视图模式

| 模式 | 布局 | 说明 |
|------|------|------|
| **Chat** (默认) | 左聊天 + 右文件树 | 主要交互模式 |
| **Focus** | 全屏聊天 | 隐藏侧边栏，专注对话 |
| **Diff** | 左原文件 + 右修改后 | 编辑预览模式 |
| **Compile** | 上聊天 + 下编译输出 | 编译调试模式 |
| **File** | 全屏文件编辑 | 内嵌文件查看（可选） |

### 1.4 颜色主题

```rust
// 深色主题（默认）
struct Theme {
    background: Color::Black,
    foreground: Color::White,
    user_message: Color::Green,       // #32FF32
    assistant_message: Color::Cyan,   // #00FFFF
    error: Color::Red,               // #FF3333
    warning: Color::Yellow,          // #FFFF00
    border: Color::DarkGray,
    accent: Color::Blue,
    input_bg: Color::Rgb(30, 30, 30),
}
```

---

## 二、Rust 项目结构

### 2.1 Crate 结构

```
lsr/
├── Cargo.toml
├── src/
│   ├── main.rs              # 入口（对应 lsr/main.py）
│   ├── lib.rs               # 库根
│   ├── app.rs               # 应用状态管理
│   ├── cli/
│   │   ├── mod.rs           # 对应 lsr/args.py
│   │   └── args.rs          # 命令行参数定义
│   ├── io/
│   │   ├── mod.rs           # 对应 lsr/io.py
│   │   ├── input.rs         # 输入处理
│   │   └── output.rs        # 输出处理
│   ├── tui/
│   │   ├── mod.rs           # TUI 入口
│   │   ├── app.rs           # TUI 应用状态
│   │   ├── event.rs         # 事件处理
│   │   ├── handler.rs       # 按键处理器
│   │   └── ui/
│   │       ├── mod.rs       # UI 渲染入口
│   │       ├── status_bar.rs
│   │       ├── chat_area.rs
│   │       ├── input_bar.rs
│   │       ├── file_tree.rs
│   │       ├── diff_view.rs
│   │       ├── command_palette.rs
│   │       └── theme.rs
│   ├── coders/
│   │   ├── mod.rs           # 对应 lsr/coders/__init__.py
│   │   ├── base.rs          # 对应 base_coder.py
│   │   ├── editblock.rs     # 对应 editblock_coder.py
│   │   ├── ask.rs           # 对应 ask_coder.py
│   │   ├── plan.rs          # 对应 plan_coder.py
│   │   ├── help.rs          # 对应 help_coder.py
│   │   └── prompts/         # 提示词模块
│   │       ├── mod.rs
│   │       ├── base.rs
│   │       ├── editblock.rs
│   │       ├── ask.rs
│   │       └── plan.rs
│   ├── commands/
│   │   ├── mod.rs           # 对应 lsr/commands.py
│   │   ├── file_ops.rs      # /add, /drop, /read
│   │   ├── git_ops.rs       # /commit, /diff, /undo
│   │   ├── latex_ops.rs     # /compile, /check, /preview
│   │   ├── model_ops.rs     # /model, /tokens
│   │   └── chat_ops.rs      # /chat, /clear, /load
│   ├── models/
│   │   ├── mod.rs           # 对应 lsr/models.py
│   │   ├── model.rs         # Model 结构体
│   │   ├── settings.rs      # 模型设置
│   │   └── registry.rs      # 模型注册
│   ├── llm/
│   │   ├── mod.rs           # 对应 lsr/llm.py
│   │   └── client.rs        # Python 子进程调用 litellm
│   ├── repo/
│   │   ├── mod.rs           # 对应 lsr/repo.py
│   │   ├── git.rs           # Git 操作
│   │   └── ignore.rs        # .gitignore 处理
│   ├── latex/
│   │   ├── mod.rs           # 对应 lsr/latex_tools.py
│   │   ├── compiler.rs      # LaTeX 编译
│   │   ├── parser.rs        # 错误解析
│   │   └── bibtex.rs        # BibTeX 处理
│   ├── history/
│   │   ├── mod.rs           # 对应 lsr/history.py
│   │   └── summary.rs       # 聊天摘要
│   ├── diffs/
│   │   └── mod.rs           # 对应 lsr/diffs.py
│   ├── linter/
│   │   └── mod.rs           # 对应 lsr/linter.py
│   └── utils/
│       ├── mod.rs           # 对应 lsr/utils.rs
│       ├── markdown.rs      # Markdown 处理
│       └── config.rs        # 配置管理
└── resources/
    └── model-metadata.json  # 模型元数据
```

### 2.2 核心依赖

```toml
[dependencies]
# TUI
ratatui = "0.30"
crossterm = "0.28"

# 异步运行时
tokio = { version = "1", features = ["full"] }

# 序列化
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"

# Git
git2 = "0.19"

# 配置
config = "0.14"
directories = "6"

# Markdown 渲染
pulldown-cmark = "0.12"
syntect = "5"  # 代码高亮

# 命令行
clap = { version = "4", features = ["derive"] }

# 日志
tracing = "0.1"
tracing-subscriber = "0.3"

# Python 子进程调用 litellm
# LLM 通过 Python 子进程调用，保持与 Python 版本完全兼容

# 其他
uuid = { version = "1", features = ["v4"] }
chrono = "0.4"
dirs = "6"
notify = "7"  # 文件监控
```

---

## 三、Python → Rust 映射

### 3.1 核心类型映射

| Python | Rust | 说明 |
|--------|------|------|
| `class Coder` | `struct Coder` + `impl Coder` | 核心编码器 |
| `class Commands` | `struct CommandRegistry` | 命令注册表 |
| `class InputOutput` | `struct Io` | I/O 抽象 |
| `class Model` | `struct Model` | LLM 模型 |
| `class GitRepo` | `struct GitRepo` | Git 仓库 |
| `class ChatSummary` | `struct ChatSummary` | 聊天摘要 |
| `class LatexCompiler` | `struct LatexCompiler` | LaTeX 编译器 |
| `dict` (messages) | `Vec<Message>` | 消息列表 |
| `dataclass` | `#[derive(Serialize, Deserialize)]` | 数据类 |

### 3.2 LLM 集成策略

**使用 Python 子进程调用 litellm**，保持与 Python 版本完全兼容：

```rust
pub struct LlmClient {
    python_path: PathBuf,
    script_path: PathBuf,
}

impl LlmClient {
    pub async fn send_messages(
        &self,
        model: &str,
        messages: &[Message],
    ) -> Result<String> {
        let input = serde_json::json!({
            "model": model,
            "messages": messages,
        });

        let output = Command::new(&self.python_path)
            .arg(&self.script_path)
            .arg("--input")
            .arg(input.to_string())
            .output()
            .await?;

        let response: serde_json::Value = serde_json::from_slice(&output.stdout)?;
        Ok(response["choices"][0]["message"]["content"].as_str().unwrap_or("").to_string())
    }
}
```

Python 辅助脚本 (`lsr_llm.py`):
```python
import sys
import json
import litellm

input_data = json.loads(sys.argv[2])
response = litellm.completion(**input_data)
print(json.dumps(response.model_dump()))
```

### 3.3 关键 Rust 设计模式

```rust
// 应用状态（替代全局变量）
pub struct App {
    pub coder: Coder,
    pub commands: CommandRegistry,
    pub io: Io,
    pub model: Model,
    pub repo: Option<GitRepo>,
    pub tui_state: TuiState,
}

// 消息类型（对应 Python dict）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: Role,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Role {
    #[serde(rename = "system")]
    System,
    #[serde(rename = "user")]
    User,
    #[serde(rename = "assistant")]
    Assistant,
}

// 编辑格式（对应 Python edit_format）
pub enum EditFormat {
    Diff,      // 搜索/替换块
    Ask,       // 纯问答
    Plan,      // 规划模式
    Help,      // 帮助模式
}

// 异步 LLM 调用
impl Model {
    pub async fn send_messages(&self, messages: &[Message]) -> Result<String> {
        // 对应 Python litellm.completion()
    }
}
```

### 3.3 异步架构

```rust
// 事件驱动的 TUI 循环
#[tokio::main]
async fn main() -> Result<()> {
    let mut terminal = ratatui::init();
    let (tx, mut rx) = tokio::sync::mpsc::channel(32);

    // 事件处理任务
    let event_tx = tx.clone();
    tokio::spawn(async move {
        loop {
            if let Ok(event) = crossterm::event::read() {
                let _ = event_tx.send(AppEvent::Terminal(event)).await;
            }
        }
    });

    // 主循环
    loop {
        terminal.draw(|frame| ui::render(frame, &app))?;

        tokio::select! {
            Some(event) = rx.recv() => {
                match event {
                    AppEvent::Terminal(key) => app.handle_key(key).await?,
                    AppEvent::LlmResponse(resp) => app.handle_llm_response(resp),
                    AppEvent::CompileResult(result) => app.handle_compile(result),
                    AppEvent::Quit => break,
                }
            }
        }
    }

    ratatui::restore();
    Ok(())
}
```

---

## 四、分阶段实施

### Phase 1: 基础框架 (1-2 周)

- [x] 创建 Cargo 项目结构
- [x] 实现 CLI 参数解析 (clap)
- [x] 实现基础 TUI 框架 (ratatui + crossterm)
- [x] 实现输入栏和聊天区域
- [x] 实现基本的 Markdown 渲染

### Phase 2: 核心功能 (2-3 周)

- [x] 实现 LLM 客户端 (Python 子进程 litellm)
- [x] 实现消息管理和上下文
- [x] 实现搜索/替换编辑器
- [x] 实现 Git 集成 (git2)
- [x] 实现基本命令 (/add, /drop, /commit, /diff)

### Phase 3: LaTeX 功能 (1-2 周)

- [x] 实现 LaTeX 编译器集成
- [x] 实现 BibTeX 处理
- [x] 实现 LaTeX 特定命令 (/compile, /check, /bib)
- [x] 实现错误解析和定位

### Phase 4: 高级功能 (2-3 周)

- [x] ~~实现 tree-sitter 代码解析~~ (不需要，面向 LaTeX)
- [x] ~~实现 RepoMap 生成~~ (不需要，面向 LaTeX)
- [x] 实现聊天历史摘要
- [x] 实现文件监控 (notify)
- [x] 实现配置管理

### Phase 5: TUI 美化 (1-2 周)

- [x] 实现文件树面板
- [x] 实现命令面板 (Ctrl+P)
- [x] 实现 Diff 视图
- [x] 实现主题系统
- [x] 实现状态栏增强

### Phase 6: 测试和优化 (1-2 周)

- [x] 单元测试
- [x] 集成测试
- [x] 性能优化
- [x] 文档编写

---

## 五、关键实现细节

### 5.1 TUI 事件处理

```rust
pub enum AppEvent {
    Terminal(crossterm::event::Event),
    LlmResponse(String),
    CompileResult(CompileResult),
    FileChanged(PathBuf),
    Quit,
}

impl App {
    pub async fn handle_key(&mut self, key: KeyEvent) -> Result<()> {
        match self.mode {
            Mode::Input => match key.code {
                KeyCode::Enter => self.submit_input().await?,
                KeyCode::Tab => self.autocomplete(),
                KeyCode::Up => self.history_prev(),
                KeyCode::Down => self.history_next(),
                KeyCode::Char('/') if self.input.is_empty() => {
                    self.show_command_palette()
                }
                _ => self.input.handle_key(key),
            },
            Mode::Chat => match key.code {
                KeyCode::Char('q') => return Ok(self.quit()),
                KeyCode::Char('i') => self.mode = Mode::Input,
                KeyCode::Char('j') => self.scroll_chat_down(),
                KeyCode::Char('k') => self.scroll_chat_up(),
                _ => {}
            },
            // ... 其他模式
        }
        Ok(())
    }
}
```

### 5.2 Markdown 渲染

```rust
use pulldown_cmark::{Parser, Options, Event, Tag};

pub fn render_markdown(text: &str) -> Vec<Line<'static>> {
    let parser = Parser::new_ext(text, Options::all());
    let mut lines = Vec::new();
    let mut current_line = Vec::new();

    for event in parser {
        match event {
            Event::Start(Tag::Heading(..)) => {
                current_line.push(Span::styled("# ", Style::default().bold()));
            }
            Event::Text(text) => {
                current_line.push(Span::raw(text.to_string()));
            }
            Event::Code(code) => {
                current_line.push(Span::styled(
                    code.to_string(),
                    Style::default().fg(Color::Yellow),
                ));
            }
            Event::End(Tag::Paragraph) => {
                lines.push(Line::from(current_line.clone()));
                current_line.clear();
            }
            // ... 其他事件
        }
    }
    lines
}
```

### 5.3 LLM 流式响应

```rust
impl Model {
    pub async fn stream_messages(
        &self,
        messages: &[Message],
        tx: mpsc::Sender<String>,
    ) -> Result<()> {
        let client = reqwest::Client::new();
        let request = self.build_request(messages);

        let mut stream = client
            .post(&self.endpoint)
            .json(&request)
            .send()
            .await?
            .bytes_stream();

        while let Some(chunk) = stream.next().await {
            let chunk = chunk?;
            // 解析 SSE 数据
            if let Some(content) = parse_sse_chunk(&chunk) {
                tx.send(content).await?;
            }
        }

        Ok(())
    }
}
```

### 5.4 Git 集成

```rust
use git2::Repository;

pub struct GitRepo {
    repo: Repository,
    root: PathBuf,
}

impl GitRepo {
    pub fn open(path: &Path) -> Result<Self> {
        let repo = Repository::discover(path)?;
        let root = repo.workdir()
            .ok_or_else(|| anyhow!("Not a working directory"))?
            .to_path_buf();
        Ok(Self { repo, root })
    }

    pub fn commit(&self, message: &str, files: &[PathBuf]) -> Result<Oid> {
        let mut index = self.repo.index()?;
        for file in files {
            index.add_path(file)?;
        }
        index.write()?;

        let tree_id = index.write_tree()?;
        let tree = self.repo.find_tree(tree_id)?;
        let signature = self.repo.signature()?;
        let parent = self.repo.head()?.peel_to_commit()?;

        self.repo.commit(
            Some("HEAD"),
            &signature,
            &signature,
            message,
            &tree,
            &[&parent],
        )
    }
}
```

---

## 六、验证方案

1. **编译检查**: `cargo build` 无错误
2. **单元测试**: `cargo test` 通过
3. **功能测试**:
   - 启动 TUI 界面正常显示
   - 输入消息能发送到 LLM
   - 接收响应并渲染 Markdown
   - `/compile` 命令能调用 LaTeX
   - Git 操作正常工作
4. **性能测试**: 启动时间 < 500ms，响应延迟 < 100ms

---

## 七、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Rust 学习曲线 | 高 | 分阶段实施，先实现核心功能 |
| LLM API 兼容性 | 中 | 使用 reqwest 直接调用，不依赖 SDK |
| Tree-sitter 集成 | 中 | 优先实现基础版本，后续优化 |
| Markdown 渲染性能 | 低 | 使用 pulldown-cmark，性能优秀 |
| 跨平台兼容 | 低 | crossterm 后端跨平台支持 |

---

## 八、后续扩展

- [ ] 插件系统 (WebAssembly)
- [x] ~~多模型并发~~ (不需要)
- [x] ~~协作编辑~~ (不需要)
- [x] ~~云端同步~~ (不需要)
- [x] ~~VS Code 集成~~ (不需要)
