# lsr UI 优化计划：Catppuccin Mocha 主题

## 背景

将 lsr 的终端 UI 颜色方案从当前的硬编码颜色迁移到 **Catppuccin Mocha** 调色板，提供更美观、一致的深色主题体验。

## Catppuccin Mocha 完整色板

### 强调色 (Accents)
| 颜色名 | Hex | 用途建议 |
|--------|-----|----------|
| Rosewater | `#f5e0dc` | 柔和高亮、链接 |
| Flamingo | `#f2cdcd` | 次要强调 |
| Pink | `#f5c2e7` | 特殊标记、LaTeX 相关 |
| Mauve | `#cba6f7` | 关键字、命令名 |
| Red | `#f38ba8` | 错误、删除 |
| Maroon | `#eba0ac` | 警告变体 |
| Peach | `#fab387` | 警告、提示 |
| Yellow | `#f9e2af` | 注意、文件名 |
| Green | `#a6e3a1` | 成功、添加 |
| Teal | `#94e2d5` | 信息、代码 |
| Sky | `#89dceb` | 次要信息 |
| Sapphire | `#74c7ec` | 链接、路径 |
| Blue | `#89b4fa` | 用户输入、主要交互 |
| Lavender | `#b4befe` | AI 助手输出 |

### 中性色 (Neutrals)
| 颜色名 | Hex | 用途建议 |
|--------|-----|----------|
| Text | `#cdd6f4` | 主要文本 |
| Subtext 1 | `#bac2de` | 次要文本 |
| Subtext 0 | `#a6adc8` | 占位符文本 |
| Overlay 2 | `#9399b2` | 边框、分隔线 |
| Overlay 1 | `#7f849c` | 禁用文本 |
| Overlay 0 | `#6c7086` | 暗淡元素 |
| Surface 2 | `#585b70` | 输入框背景 |
| Surface 1 | `#45475a` | 卡片背景 |
| Surface 0 | `#313244` | 容器背景 |
| Base | `#1e1e2e` | 主背景 |
| Mantle | `#181825` | 次要背景 |
| Crust | `#11111b` | 最深背景 |

---

## 修改方案

### 1. 创建主题配置模块

**新建文件**: `lsr/theme.py`

```python
"""Catppuccin Mocha theme configuration for lsr."""

# Catppuccin Mocha Color Palette
class CatppuccinMocha:
    """Catppuccin Mocha theme colors."""
    
    # Accents
    ROSEWATER = "#f5e0dc"
    FLAMINGO = "#f2cdcd"
    PINK = "#f5c2e7"
    MAUVE = "#cba6f7"
    RED = "#f38ba8"
    MAROON = "#eba0ac"
    PEACH = "#fab387"
    YELLOW = "#f9e2af"
    GREEN = "#a6e3a1"
    TEAL = "#94e2d5"
    SKY = "#89dceb"
    SAPPHIRE = "#74c7ec"
    BLUE = "#89b4fa"
    LAVENDER = "#b4befe"
    
    # Neutrals
    TEXT = "#cdd6f4"
    SUBTEXT1 = "#bac2de"
    SUBTEXT0 = "#a6adc8"
    OVERLAY2 = "#9399b2"
    OVERLAY1 = "#7f849c"
    OVERLAY0 = "#6c7086"
    SURFACE2 = "#585b70"
    SURFACE1 = "#45475a"
    SURFACE0 = "#313244"
    BASE = "#1e1e2e"
    MANTLE = "#181825"
    CRUST = "#11111b"


# Semantic color mapping for lsr
THEME = {
    # User interaction
    "user_input_color": CatppuccinMocha.BLUE,
    "user_prompt_color": CatppuccinMocha.SAPPHIRE,
    
    # Tool output
    "tool_output_color": CatppuccinMocha.TEXT,
    "tool_error_color": CatppuccinMocha.RED,
    "tool_warning_color": CatppuccinMocha.PEACH,
    "tool_success_color": CatppuccinMocha.GREEN,
    "tool_info_color": CatppuccinMocha.TEAL,
    
    # AI Assistant
    "assistant_output_color": CatppuccinMocha.LAVENDER,
    "assistant_thinking_color": CatppuccinMocha.OVERLAY1,
    
    # Code & Syntax
    "code_theme": "catppuccin-mocha",  # 需要自定义或使用兼容主题
    "code_keyword_color": CatppuccinMocha.MAUVE,
    "code_string_color": CatppuccinMocha.GREEN,
    "code_comment_color": CatppuccinMocha.OVERLAY1,
    
    # UI Elements
    "border_color": CatppuccinMocha.OVERLAY2,
    "separator_color": CatppuccinMocha.SURFACE2,
    "highlight_bg": CatppuccinMocha.SURFACE0,
    "selection_bg": CatppuccinMocha.SURFACE1,
    
    # Status indicators
    "status_success": CatppuccinMocha.GREEN,
    "status_error": CatppuccinMocha.RED,
    "status_warning": CatppuccinMocha.YELLOW,
    "status_info": CatppuccinMocha.SKY,
    "status_processing": CatppuccinMocha.MAUVE,
    
    # File & Path
    "file_name_color": CatppuccinMocha.YELLOW,
    "path_color": CatppuccinMocha.SAPPHIRE,
    "line_number_color": CatppuccinMocha.OVERLAY0,
    
    # Completion menu
    "completion_menu_color": CatppuccinMocha.TEXT,
    "completion_menu_bg_color": CatppuccinMocha.SURFACE0,
    "completion_menu_current_color": CatppuccinMocha.BASE,
    "completion_menu_current_bg_color": CatppuccinMocha.MAUVE,
    
    # Prompt
    "prompt_prefix_color": CatppuccinMocha.LAVENDER,
    "prompt_continuation_color": CatppuccinMocha.OVERLAY1,
}
```

---

### 2. 修改文件清单

#### 核心文件

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `lsr/theme.py` | 新建：主题配置模块 | P0 |
| `lsr/io.py` | 替换所有硬编码颜色为 theme 引用 | P0 |
| `lsr/mdstream.py` | 更新 Markdown 渲染主题 | P0 |
| `lsr/waiting.py` | 更新 spinner 颜色 | P1 |
| `lsr/editor.py` | 更新状态消息颜色 | P2 |
| `lsr/commands.py` | 更新命令输出颜色 | P1 |
| `lsr/coders/base_coder.py` | 更新 coder 输出样式 | P1 |
| `lsr/onboarding.py` | 更新欢迎界面颜色 | P2 |
| `lsr/repomap.py` | 更新树状图颜色 | P2 |

---

### 3. 详细修改方案

#### 3.1 `lsr/io.py` 修改

```python
# 在文件顶部添加
from lsr.theme import THEME, CatppuccinMocha as Mocha

# 修改 IO 类初始化参数
class InputOutput:
    def __init__(
        self,
        pretty=True,
        ...
        # 替换原来的默认颜色
        user_input_color=THEME["user_input_color"],
        tool_output_color=THEME["tool_output_color"],
        tool_error_color=THEME["tool_error_color"],
        tool_warning_color=THEME["tool_warning_color"],
        assistant_output_color=THEME["assistant_output_color"],
        completion_menu_color=THEME["completion_menu_color"],
        completion_menu_bg_color=THEME["completion_menu_bg_color"],
        completion_menu_current_color=THEME["completion_menu_current_color"],
        completion_menu_current_bg_color=THEME["completion_menu_current_bg_color"],
        code_theme="monokai",  # 保持 monokai 或切换到 catppuccin 兼容主题
    ):
        ...

    def tool_output(self, *messages, log_only=False, bold=False):
        """使用 Mocha 主题的 tool_output"""
        if self.pretty:
            if bold:
                style = RichStyle(
                    color=THEME["tool_output_color"],
                    bgcolor=Mocha.SURFACE0,
                    bold=True
                )
            else:
                style = RichStyle(color=THEME["tool_output_color"])
        ...
```

#### 3.2 `lsr/mdstream.py` 修改

```python
from lsr.theme import CatppuccinMocha as Mocha

class NoInsetCodeBlock(CodeBlock):
    """使用 Catppuccin Mocha 配色的代码块"""
    def __rich_console__(self, console, options):
        code = str(self.text).rstrip()
        syntax = Syntax(
            code,
            self.lexer_name,
            theme="monokai",  # 或使用 catppuccin 兼容的 Pygments 主题
            word_wrap=True,
            padding=(1, 0),
            background_color=Mocha.BASE,  # 使用 Base 作为代码块背景
        )
        yield syntax

class LeftHeading(Heading):
    """使用 Mocha 主色的标题"""
    def __rich_console__(self, console, options):
        text = self.text
        text.justify = "left"
        if self.tag == "h1":
            text.stylize(f"bold {Mocha.LAVENDER}")
            yield text
            yield Text("─" * min(console.width or 80, 80), style=Mocha.SURFACE2)
        elif self.tag == "h2":
            text.stylize(f"bold {Mocha.MAUVE}")
            yield Text("")
            yield text
        else:
            text.stylize(f"bold {Mocha.SAPPHIRE}")
            yield text
```

#### 3.3 `lsr/waiting.py` 修改

```python
from lsr.theme import CatppuccinMocha as Mocha

class Spinner:
    def __init__(self, text: str, width: int = 7):
        ...
        # 使用 Mocha 主题颜色
        self.scan_color = Mocha.MAUVE  # 扫描字符颜色
        self.text_color = Mocha.SUBTEXT1  # 文本颜色
```

#### 3.4 命令输出样式

```python
# 在 commands.py 中
from lsr.theme import THEME, CatppuccinMocha as Mocha

class Commands:
    def cmd_tokens(self, args):
        ...
        # Token 显示使用 Mocha 颜色
        self.io.tool_output(
            f"{cost_pad}{fmt(tokens)} tokens", 
            style=Mocha.SKY
        )
        ...
    
    def cmd_diff(self, args=""):
        ...
        # Diff 输出使用语义颜色
        # 添加行: Green
        # 删除行: Red
        # 上下文: Subtext
```

---

### 4. 代码块语法高亮

由于 Rich 的 Syntax 组件使用 Pygments 主题，我们需要：

**选项 A**: 使用 `monokai` 主题（与 Mocha 风格接近）
**选项 B**: 创建自定义 Pygments 主题映射 Catppuccin Mocha 颜色

推荐先使用 **选项 A**，后续可创建自定义主题。

---

### 5. 实现步骤

- [ ] **Step 1**: 创建 `lsr/theme.py` 主题配置文件
- [ ] **Step 2**: 修改 `lsr/io.py` 集成主题配置
- [ ] **Step 3**: 更新 `lsr/mdstream.py` Markdown 渲染颜色
- [ ] **Step 4**: 更新 `lsr/waiting.py` spinner 颜色
- [ ] **Step 5**: 更新 `lsr/commands.py` 命令输出样式
- [ ] **Step 6**: 更新 `lsr/coders/base_coder.py` coder 输出
- [ ] **Step 7**: 更新 `lsr/editor.py` 状态消息
- [ ] **Step 8**: 更新 `lsr/onboarding.py` 欢迎界面
- [ ] **Step 9**: 测试并调整对比度和可读性

---

### 6. 验证方案

1. **视觉测试**
   ```bash
   # 启动 lsr 检查各组件颜色
   lsr --model gpt-4
   ```

2. **检查点**
   - [ ] 用户输入提示符颜色正确
   - [ ] 错误消息显示为 Red
   - [ ] 警告消息显示为 Peach
   - [ ] AI 回复使用 Lavender
   - [ ] 代码块背景为 Base 色
   - [ ] 补全菜单样式正确
   - [ ] Spinner 动画颜色协调

3. **NO_COLOR 兼容性**
   ```bash
   NO_COLOR=1 lsr  # 应该禁用所有颜色
   ```

---

### 7. 额外 UI 美化

#### 7.1 状态栏 (Status Bar)
**新建文件**: `lsr/status_bar.py`

```python
"""底部状态栏显示当前上下文信息"""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from lsr.theme import CatppuccinMocha as Mocha

class StatusBar:
    def __init__(self, io):
        self.io = io
        self.console = io.console
    
    def render(self, context):
        """渲染状态栏
        context: dict with keys:
            - model: str (当前模型名)
            - files: list (已添加文件数)
            - tokens: int (已用tokens)
            - edit_format: str (当前编辑格式)
        """
        left = Text()
        left.append(" ⚡ ", style=Mocha.YELLOW)
        left.append(f"{context.get('model', 'unknown')}", style=Mocha.LAVENDER)
        left.append(" │ ", style=Mocha.SURFACE2)
        left.append(f"📁 {len(context.get('files', []))} files", style=Mocha.SKY)
        left.append(" │ ", style=Mocha.SURFACE2)
        left.append(f"🔤 {context.get('tokens', 0):,} tokens", style=Mocha.TEAL)
        
        right = Text()
        right.append(f"{context.get('edit_format', 'ask')} ", style=Mocha.SUBTEXT1)
        right.append("│ Ctrl-C: interrupt │ /help: help", style=Mocha.OVERLAY1)
        
        bar = Panel(
            left,
            style=f"on {Mocha.MANTLE}",
            border_style=Mocha.SURFACE2,
            height=1
        )
        self.console.print(bar)
```

#### 7.2 分栏布局 (Columns)
用于 `/tokens`, `/ls` 等命令的分栏显示：

```python
from rich.columns import Columns
from rich.table import Table
from lsr.theme import CatppuccinMocha as Mocha

def render_file_table(files, token_counts):
    """使用 Rich Table 渲染文件列表"""
    table = Table(
        show_header=True,
        header_style=f"bold {Mocha.MAUVE}",
        border_style=Mocha.SURFACE2,
        title="Chat Files",
        title_style=f"bold {Mocha.LAVENDER}"
    )
    table.add_column("Tokens", style=Mocha.TEAL, justify="right")
    table.add_column("File", style=Mocha.YELLOW)
    table.add_column("Status", style=Mocha.OVERLAY1)
    
    for fname, tokens in zip(files, token_counts):
        table.add_row(f"{tokens:,}", fname, "/drop to remove")
    
    return table
```

#### 7.3 增强的 Diff 显示
**修改**: `lsr/diffs.py`

```python
from rich.syntax import Syntax
from rich.text import Text
from lsr.theme import CatppuccinMocha as Mocha

def render_diff(old, new, filename):
    """渲染带语法高亮的 diff"""
    # 使用 Rich Syntax 进行 side-by-side diff
    from rich.columns import Columns
    
    old_syntax = Syntax(
        old, "python",
        theme="monokai",
        line_numbers=True,
        background_color=Mocha.BASE
    )
    new_syntax = Syntax(
        new, "python",
        theme="monokai",
        line_numbers=True,
        background_color=Mocha.BASE
    )
    
    return Columns([old_syntax, new_syntax])
```

#### 7.4 交互式确认框
```python
from rich.panel import Panel
from rich.prompt import Confirm
from lsr.theme import CatppuccinMocha as Mocha

def styled_confirm(message, default=True):
    """Mocha 风格的确认对话框"""
    panel = Panel(
        f"[bold]{message}[/bold]\n[dim]\[y/N][/dim]",
        title="[bold]Confirm[/bold]",
        border_style=Mocha.PEACH,
        style=f"on {Mocha.SURFACE0}"
    )
    # 实现交互逻辑
```

#### 7.5 进度指示器
**修改**: `lsr/waiting.py` 增加进度条支持

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from lsr.theme import CatppuccinMocha as Mocha

class ProgressIndicator:
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(style=Mocha.MAUVE),
            TextColumn("[progress.description]{task.description}", style=Mocha.TEXT),
            BarColumn(
                complete_style=Mocha.GREEN,
                finished_style=Mocha.GREEN,
                pulse_style=Mocha.MAUVE
            ),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style=Mocha.TEAL),
        )
```

---

### 8. 后续优化（可选）

| 优化项 | 说明 |
|--------|------|
| 自定义 Pygments 主题 | 创建完全匹配 Mocha 的语法高亮主题 |
| 主题切换支持 | 支持 Latte/Frapé/Macchiato/Mocha 切换 |
| 配置文件支持 | 允许用户自定义颜色覆盖 |
| 终端背景检测 | 自动检测终端背景选择合适的主题变体 |

---

## 预期效果

应用 Catppuccin Mocha 主题后，lsr 将具有：
- 🎨 统一协调的深色主题
- 👁️ 良好的对比度和可读性
- 🌙 护眼的低饱和度配色
- ✨ 清晰的语义颜色区分（错误/警告/成功）
