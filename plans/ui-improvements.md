# LSR UI 改进方案

## 目标
优化 Python 版 LSR 的终端 UI，提升用户体验，同时保持代码简洁。

---

## 一、当前问题分析

### 1.1 颜色系统
| 问题 | 现状 | 改进 |
|------|------|------|
| 用户输入颜色 | 蓝色 (blue) | 蓝色在深色终端对比度低，建议改为 **cyan** 或 **green** |
| 警告颜色 | 橙色 (#FFA500) | OK，保持 |
| 错误颜色 | 红色 (red) | OK，保持 |
| 工具输出 | 无色 | 可选：添加淡灰色以区分 |

### 1.2 输入体验
| 问题 | 现状 | 改进 |
|------|------|------|
| 命令补全 | 有，但不够直观 | Tab 补全显示可用命令列表 |
| 历史记录 | 有 | OK |
| 多行输入 | 有 | OK |

### 1.3 输出渲染
| 问题 | 现状 | 改进 |
|------|------|------|
| Markdown 渲染 | Rich 渲染 | OK，但长消息可能截断 |
| 差异显示 | 基础 diff | 可添加语法高亮 |
| 进度反馈 | 无 | LLM 响应时显示 spinner |

---

## 二、改进方案（按优先级）

### P0: 颜色优化（最小改动）

```python
# lsr/io.py - 修改默认颜色
user_input_color="cyan",      # 原 blue，提升对比度
tool_output_color=None,        # 保持无色
tool_error_color="red",        # 保持
tool_warning_color="#FFA500",  # 保持
```

**验证**：在深色终端中测试输入提示的可见性。

### P1: 状态栏增强

添加底部状态栏显示：
- 当前模型名称
- 已加载文件数
- Git 分支
- Token 使用量（如有）

```python
# 新增方法
def render_status_bar(self):
    """渲染底部状态栏"""
    parts = []
    if self.model:
        parts.append(f"Model: {self.model.name}")
    parts.append(f"Files: {len(self.abs_fnames)}")
    # ... Git 信息
    self.console.print(" │ ".join(parts), style="dim")
```

### P2: LLM 响应进度

在等待 LLM 响应时显示 spinner：

```python
from rich.spinner import Spinner
from rich.live import Live

def get_input_with_spinner(self, prompt):
    """带 spinner 的输入等待"""
    with Live(Spinner("dots", style="cyan"), refresh_per_second=10):
        # 等待 LLM 响应
        pass
```

### P3: 命令帮助优化

改进 `/help` 命令输出格式：

```
可用命令：
  /add <file>      添加文件到聊天
  /run <cmd>       执行 shell 命令
  /diff            查看当前差异
  /undo            撤销上次编辑
  /help            显示此帮助
```

---

## 三、实施步骤

1. **P0 颜色优化** — 10 分钟
   - 修改 `lsr/io.py` 第 257 行
   - 测试：启动 lsr，观察输入提示颜色

2. **P1 状态栏** — 30 分钟
   - 在 `IO` 类添加 `render_status_bar()` 方法
   - 在 `get_input()` 调用前渲染
   - 测试：检查状态栏信息准确性

3. **P2 Spinner** — 20 分钟
   - 在 `Coder` 类的 LLM 调用处添加 spinner
   - 测试：发送消息，观察加载动画

4. **P3 帮助优化** — 15 分钟
   - 修改 `commands.py` 的 `/help` 命令
   - 测试：运行 `/help` 查看格式

---

## 四、验证清单

- [ ] 深色终端中输入提示清晰可见
- [ ] 状态栏显示正确信息
- [ ] LLM 响应时有进度反馈
- [ ] `/help` 输出格式整洁
- [ ] 不影响现有功能

---

## 五、不做的事

- ❌ 不引入新依赖（Rich 和 prompt_toolkit 已足够）
- ❌ 不重构 IO 架构（当前设计合理）
- ❌ 不添加复杂主题系统（保持简单）
- ❌ 不添加 vim 模式（用户明确不喜欢）

---

## 六、Rust TUI 对比

此方案优化 Python 版 UI，与 Rust TUI 重写并行进行：
- Python 版：快速迭代，验证 UI 设计
- Rust 版：长期方案，性能更好

UI 设计经验可迁移到 Rust 版。
