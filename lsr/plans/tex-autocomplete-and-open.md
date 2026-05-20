# Plan: `/edit` 添加 tex 文件自动补全 + 新增 `/open` 命令

## Context

当前 `/edit` 命令需要用户精确输入完整的 `.tex` 文件名（如 `/edit chapter1.tex`），没有任何自动补全提示，使用不方便。需要：

1. **给 `/edit` 添加 tex 文件补全**：类似 `/add` 命令，用户输入 `/edit ` 后自动提示项目中的 `.tex` 文件
2. **新增 `/open` 命令**：交互式选择已 `/add` 的文件，用 neovim 在新终端窗口中打开

## Approach

### 功能 1：`/edit` 添加 tex 文件自动补全

**核心机制**：lsr 的补全系统通过命名约定工作：
- `completions_{cmd}()` → 返回简单字符串列表（适合静态候选）
- `completions_raw_{cmd}(document, complete_event)` → 返回 prompt_toolkit Completion 对象（适合动态/路径补全）

**方案**：添加 `completions_edit()` 方法，扫描项目目录中的 `.tex` 文件作为补全候选。

实现逻辑：
1. 从 `self.coder.get_all_relative_files()` 获取所有文件
2. 过滤出 `.tex` 后缀的文件
3. 同时加入 `self.coder.get_inchat_relative_files()` 中的 `.tex` 文件（已 add 的）
4. 去重后用 `self.quote_fname()` 处理文件名中的空格
5. 返回排序列表

这与 `completions_add()` 的实现几乎一致，只是多了一步 `.tex` 过滤。

### 功能 2：`/open` 命令

**方案**：添加 `cmd_open()` 方法，流程如下：
1. 获取当前已 `/add` 的文件列表（`self.coder.get_inchat_relative_files()`）
2. 如果没有参数，交互式列出文件让用户选择（编号选择，复用 `/edit` 的交互模式）
3. 如果有参数（文件名），直接匹配
4. 使用 `subprocess.Popen` 在新终端中打开 neovim：
   - 检测终端模拟器（优先使用当前终端环境）
   - 使用 `setsid nvim {file} &` 在后台新进程打开
   - 或使用 `tmux new-window` / `screen` 等方式（如果检测到 tmux 环境）

**终端打开策略**（按优先级）：
1. 如果在 `tmux` 中运行 → `tmux new-window 'nvim {file}'`
2. 否则 → `setsid /usr/bin/env nvim {file} &`（后台进程，不阻塞 lsr）

**交互式选择**：
- 列出所有已 add 的文件（编号）
- 用户输入编号选择
- 也支持直接传文件名：`/open chapter1.tex`

## Files to modify

| 文件              | 修改内容                                                                              |
| ----------------- | ------------------------------------------------------------------------------------- |
| `lsr/commands.py` | 1. 添加 `completions_edit()` 方法<br>2. 添加 `cmd_open()` 方法                        |

## Reuse

- **`completions_add()`**（line 760）：复用其获取文件列表 + `quote_fname` 的模式
- **`self.coder.get_all_relative_files()`**：获取项目中所有文件
- **`self.coder.get_inchat_relative_files()`**：获取已 add 的文件
- **`self.quote_fname()`**（line 698）：处理文件名中的空格
- **`_parse_and_select_sections()`**（line 2071）：复用交互式选择的 UI 模式（编号列表 + 用户输入）
- **`self.io.tool_output()` / `self.io.tool_error()`**：输出信息

## Steps

- [ ] 1. 在 `commands.py` 中添加 `completions_edit()` 方法
  - 获取所有 `.tex` 文件（包括项目文件和已 add 文件）
  - 过滤 `.tex` 后缀
  - 用 `quote_fname` 处理后返回排序列表
- [ ] 2. 在 `commands.py` 中添加 `cmd_open()` 方法
  - 获取已 add 的文件列表
  - 无参数时：列出文件让用户交互选择
  - 有参数时：匹配文件名
  - 在新终端/新窗口中用 neovim 打开选中文件
- [ ] 3. 在 `commands.py` 中添加 `completions_open()` 方法
  - 提供已 add 文件的补全（类似 `completions_drop()`）

## Detailed Implementation

### `completions_edit()` (约 10 行)

```python
def completions_edit(self):
    """Provide .tex file completions for /edit command."""
    all_files = set(self.coder.get_all_relative_files())
    inchat_files = set(self.coder.get_inchat_relative_files())
    tex_files = (all_files | inchat_files)
    tex_files = [f for f in tex_files if f.endswith('.tex')]
    tex_files = [self.quote_fname(fn) for fn in tex_files]
    return tex_files
```

### `cmd_open()` (约 60 行)

```python
def cmd_open(self, args=""):
    "Open a file in neovim in a new terminal window"
    import shutil

    # Get all added files
    editable_files = list(self.coder.get_inchat_relative_files())
    read_only_files = [
        self.coder.get_rel_fname(fn) for fn in self.coder.abs_read_only_fnames
    ]
    all_files = editable_files + read_only_files

    if not all_files:
        self.io.tool_error("No files in the chat. Use /add first.")
        return

    if args.strip():
        # Direct file name provided
        filename = args.strip()
        abs_path = self.coder.abs_root_path(filename)
        if not os.path.exists(abs_path):
            # Try substring match
            matches = [f for f in all_files if filename in f]
            if len(matches) == 1:
                abs_path = self.coder.abs_root_path(matches[0])
            elif len(matches) > 1:
                self.io.tool_error(f"Multiple matches: {matches}")
                return
            else:
                self.io.tool_error(f"File not found: {filename}")
                return
    else:
        # Interactive selection
        self.io.tool_output("\n\u001b[1mFiles in chat:\u001b[0m")
        for idx, f in enumerate(all_files, 1):
            self.io.tool_output(f"  {idx}. {f}")

        selection = input("\nSelect file to open: ").strip()
        if not selection or selection.lower() == 'q':
            return

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(all_files):
                abs_path = self.coder.abs_root_path(all_files[idx])
            else:
                self.io.tool_error("Invalid selection.")
                return
        except ValueError:
            self.io.tool_error("Invalid input.")
            return

    # Open in neovim
    editor = shutil.which("nvim") or shutil.which("vim") or "vi"
    
    # Detect tmux session
    in_tmux = os.environ.get("TMUX") is not None
    
    try:
        if in_tmux:
            subprocess.Popen(
                ["tmux", "new-window", "-n", os.path.basename(abs_path), editor, abs_path],
                start_new_session=True,
            )
        else:
            # Fallback: launch in background with setsid
            subprocess.Popen(
                ["setsid", editor, abs_path],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        self.io.tool_output(f"Opened {abs_path} in {editor}")
    except Exception as e:
        self.io.tool_error(f"Failed to open file: {e}")
```

### `completions_open()` (约 10 行)

```python
def completions_open(self):
    """Provide completions for /open command - files in chat."""
    files = self.coder.get_inchat_relative_files()
    read_only_files = [
        self.coder.get_rel_fname(fn) for fn in self.coder.abs_read_only_fnames
    ]
    all_files = files + read_only_files
    all_files = [self.quote_fname(fn) for fn in all_files]
    return all_files
```

## Verification

1. **tex 补全测试**：
   - 启动 lsr，在一个有 `.tex` 文件的目录中
   - 输入 `/edit ` → 应自动弹出 `.tex` 文件列表
   - 输入 `/edit ch` → 应过滤匹配的 `.tex` 文件
   - 选择文件后按回车 → 应正常进入 section 选择

2. **`/open` 测试**：
   - 先 `/add` 几个文件
   - `/open` → 应列出已 add 的文件，输入编号后在新窗口打开
   - `/open chapter1.tex` → 应直接打开该文件
   - `/open` 无文件在 chat → 应提示 "No files"

3. **边界测试**：
   - `/edit` 无参数 → 应显示 usage（现有行为不变）
   - `/open` 输入无效编号 → 应报错
   - 无 tmux 环境下的 `/open` → 应使用 setsid 后备方案
