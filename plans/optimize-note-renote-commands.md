# Plan: `/clear` & `/drop` 缓存影响分析 + `/note` & `/renote` 命令优化

## Context

lsr 是一个基于 aider 的 LaTeX 编辑助手，支持 `/edit`、`/note`、`/renote`、`/mark` 等斜杠命令。用户提出两个需求：

1. **分析 `/clear` 和 `/drop` 对提示词缓存的影响**，以及不使用 `/clear` 时对话历史是否持续累加。
2. **优化 `/note` 和 `/renote`**：给 `/note` 添加 tex 文件嗅探；让 `/renote` 和 `/note` 能像 `/mark` 一样交互选择由 `/edit` 创建的临时文件。

---

## 第一部分：`/clear` 和 `/drop` 对提示词缓存的影响分析

### 消息组装架构

每次 LLM 请求，`format_messages()` → `format_chat_chunks()` 组装消息：

```
ChatChunks 结构:
  system          ← 系统提示词 + examples
  examples        ← 示例对话
  readonly_files  ← 只读文件内容
  repo            ← repo map
  done            ← done_messages (历史对话)
  chat_files      ← 当前可编辑文件内容
  cur             ← cur_messages (当前轮对话)
  reminder        ← 系统提醒
```

### 提示词缓存机制

在 `ChatChunks.add_cache_control_headers()` 中，缓存在 3 个断点插入：

1. **`system` 或 `examples` 尾部** — 系统提示词被缓存
2. **`repo` 或 `readonly_files` 尾部** — 文件上下文被缓存
3. **`chat_files` 尾部** — 当前文件内容被缓存

这意味着：
- `system` → `examples` → `readonly_files` → `repo` → **cache point** → `done` → `chat_files` → **cache point** → `cur`
- `done_messages`（历史对话）在缓存点之后，**不参与缓存**

### `/clear` 的影响

```python
def _clear_chat_history(self):
    self.coder.done_messages = []
    self.coder.cur_messages = []
```

- **对缓存无负面影响**：`done_messages` 本身就不在缓存范围内（它在 `chat_files` cache point 之后）
- `/clear` 清空 `done_messages` 和 `cur_messages`，反而减少了 token 消耗
- **系统提示词 + 文件内容**的缓存不受影响，因为它们由 `system`/`chat_files` 决定

### `/drop` 的影响

```python
def _drop_all_files(self):
    self.coder.abs_fnames = set()
    # ... 处理 read-only files
```

- **会破坏 `chat_files` 缓存**：`chat_files` 的内容由 `abs_fnames` 决定，`/drop` 清空后文件列表变化 → `chat_files` 内容变化 → 缓存失效
- `system` 和 `repo` 的缓存不受影响（只要 repo map 没变）

### 不使用 `/clear` 的对话历史行为

**是的，对话历史会持续累加**：

```python
def move_back_cur_messages(self, message):
    self.done_messages += self.cur_messages   # ← 每轮追加
    self.summarize_start()                     # ← 但有自动摘要机制
    self.cur_messages = []
```

- 每轮对话后，`cur_messages` 被追加到 `done_messages`
- **但有自动摘要（`ChatSummary`）**：当 `done_messages` 超过 `max_chat_history_tokens` 时，后台线程会自动压缩历史
- 所以不会无限增长，但摘要本身会丢失细节

### 结论

| 命令 | 对缓存的影响 | 建议 |
|------|-------------|------|
| `/clear` | ✅ 不影响缓存（历史在缓存断点之后），节省 token | 长对话时推荐使用 |
| `/drop` | ⚠️ 破坏 `chat_files` 缓存，因为文件列表变化 | 只在需要释放文件时使用 |
| 不用 `/clear` | 对话历史持续累加 → 自动摘要 → 细节丢失 | 不影响缓存，但 token 消耗增加 |

---

## 第二部分：`/note` 和 `/renote` 优化

### 当前行为

| 命令 | 当前行为 | 问题 |
|------|---------|------|
| `/note <file.tex>` | 交互选择 section → 创建 `lsr_note_*.tex` → 打开浏览器 | 需要手动输入文件路径，不能自动嗅探 |
| `/renote` | 只搜索 `lsr_note_*.tex.session` → 重新打开最新一个 | 忽略了 `/edit` 创建的 `lsr_edit_*.tex` 临时文件 |

### 优化 1：给 `/note` 添加 tex 文件类型嗅探

**目标**：当用户不传参数调用 `/note` 时，自动嗅探当前目录下的 `.tex` 文件（类似 `/edit` 的行为）。

**实现方案**：修改 `cmd_note` 和 `_parse_and_select_sections`：

```python
def _parse_and_select_sections(self, args, action_verb="edit"):
    if not args:
        # 新增：自动嗅探 .tex 文件
        candidates = self._find_tex_files()
        if len(candidates) == 1:
            args = candidates[0]
            self.io.tool_output(f"Auto-detected: {args}")
        elif len(candidates) > 1:
            # 交互选择文件（类似 /mark 的体验）
            self.io.tool_output("\nMultiple .tex files found:")
            for i, f in enumerate(candidates, 1):
                self.io.tool_output(f"  {i}. {f}")
            sel = input("Select file (number): ")
            try:
                idx = int(sel) - 1
                args = candidates[idx]
            except (ValueError, IndexError):
                return None
        else:
            self.io.tool_output(f"Usage: /{action_verb} <file.tex>")
            return None
    # ... 后续逻辑不变
```

**新增辅助方法**：

```python
def _find_tex_files(self):
    """Find .tex files in current directory / git repo."""
    candidates = []
    # 1. 从 abs_fnames 和 abs_read_only_fnames 中找
    for fpath in self.coder.abs_fnames | self.coder.abs_read_only_fnames:
        if fpath.endswith('.tex'):
            candidates.append(self.coder.get_rel_fname(fpath))
    # 2. 从 git repo 中搜索 .tex 文件
    if not candidates and self.coder.repo:
        for f in self.coder.repo.get_tracked_files():
            if f.endswith('.tex'):
                candidates.append(f)
    # 3. 从当前目录搜索
    if not candidates:
        for f in os.listdir('.'):
            if f.endswith('.tex'):
                candidates.append(f)
    return sorted(set(candidates))
```

### 优化 2：让 `/renote` 和 `/note` 能选择 `/edit` 创建的临时文件

**目标**：当 `/edit` 已经创建了 `lsr_edit_*.tex` 临时文件，`/renote` 和 `/note` 无参数时能交互选择这些临时文件进行 HTML 预览渲染。

**实现方案**：修改 `cmd_renote` 和 `cmd_note` 的无参数分支。

#### 修改 `cmd_renote`：

```python
def cmd_renote(self, args=""):
    """Re-open note review HTML for an existing temp file (edit or note)."""
    import glob
    import webbrowser

    from lsr.note_html import generate_note_html
    from lsr.note_server import NoteServer

    lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")

    # 搜索所有临时 session 文件（edit + note）
    edit_pattern = os.path.join(lsr_home, "lsr_edit_*.tex.session")
    note_pattern = os.path.join(lsr_home, "lsr_note_*.tex.session")
    all_sessions = glob.glob(edit_pattern) + glob.glob(note_pattern)

    if not all_sessions:
        self.io.tool_error("No session found. Use /edit or /note first.")
        return

    # 如果只有一个 session，直接使用
    if len(all_sessions) == 1:
        session_file = all_sessions[0]
    else:
        # 交互选择（类似 /mark 的体验）
        session_file = self._select_session_interactive(all_sessions)
        if session_file is None:
            return

    # ... 后续打开 HTML 浏览器的逻辑不变
```

#### 新增交互选择方法 `_select_session_interactive`：

```python
def _select_session_interactive(self, session_files):
    """让用户交互选择一个 session 文件（edit 或 note 临时文件）。"""
    self.io.tool_output("\nAvailable sessions:")
    for i, sf in enumerate(sorted(session_files, key=os.path.getmtime, reverse=True), 1):
        basename = os.path.basename(sf)
        mtime = os.path.getmtime(sf)
        import time
        time_str = time.strftime("%H:%M:%S", time.localtime(mtime))
        # 从 session 读取元信息
        try:
            with open(sf, encoding="utf-8") as f:
                session = json.load(f)
            original = os.path.basename(session.get("original_file", "unknown"))
            action = session.get("action", "edit")
            sections = len(session.get("sections", []))
            self.io.tool_output(
                f"  {i}. [{action}] {original} ({sections} sections) — {time_str}"
            )
        except Exception:
            self.io.tool_output(f"  {i}. {basename} — {time_str}")

    self.io.tool_output("  q. Cancel")
    sel = input("\nSelect session: ")
    if not sel or sel.lower() == 'q':
        return None
    try:
        idx = int(sel) - 1
        sorted_files = sorted(session_files, key=os.path.getmtime, reverse=True)
        return sorted_files[idx]
    except (ValueError, IndexError):
        return None
```

#### 修改 `cmd_note` 无参数分支：

当 `/note` 无参数时：
1. 先检查是否有 `/edit` 创建的临时文件 → 交互选择 → 直接进入 HTML 预览
2. 如果没有临时文件 → 进行 tex 文件嗅探 → 交互选择 section → 创建 note 临时文件 → HTML 预览

```python
def cmd_note(self, args=""):
    """Review LaTeX sections in browser with highlight and comments."""
    import glob
    import webbrowser

    from lsr.latex_tools import extract_text_environments
    from lsr.note_html import generate_note_html
    from lsr.note_server import NoteServer

    lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")

    # 无参数时：先检查是否有现存的 edit/note session
    if not args:
        edit_pattern = os.path.join(lsr_home, "lsr_edit_*.tex.session")
        note_pattern = os.path.join(lsr_home, "lsr_note_*.tex.session")
        all_sessions = glob.glob(edit_pattern) + glob.glob(note_pattern)

        if all_sessions:
            # 有现存 session → 交互选择 → 直接渲染 HTML
            if len(all_sessions) == 1:
                session_file = all_sessions[0]
            else:
                session_file = self._select_session_interactive(all_sessions)

            if session_file is None:
                return

            # 直接从 session 渲染 HTML（复用 renote 的逻辑）
            return self._render_session_as_html(session_file)

        # 没有现存 session → tex 文件嗅探 + section 选择（走正常流程）
        # _parse_and_select_sections 已支持无参数嗅探

    # 原有的 section 选择 + HTML 渲染逻辑...
```

#### 新增 `_render_session_as_html` 统一渲染方法：

```python
def _render_session_as_html(self, session_file):
    """从 session 文件渲染 HTML 预览（/note 和 /renote 共享）。"""
    import webbrowser
    import json

    from lsr.latex_tools import extract_text_environments
    from lsr.note_html import generate_note_html
    from lsr.note_server import NoteServer

    with open(session_file, encoding="utf-8") as f:
        session = json.load(f)

    tmp_file = session_file.replace(".session", "")
    if not os.path.exists(tmp_file):
        self.io.tool_error(f"Preview file not found: {tmp_file}")
        return

    original_file = session.get("original_file", "unknown.tex")
    filename = os.path.basename(original_file)

    # 从临时文件解析段落
    with open(tmp_file, encoding="utf-8") as f:
        content = f.read()

    paragraphs = self._extract_paragraphs_from_temp(content)

    if not paragraphs:
        self.io.tool_error("No text content found in temp file.")
        return

    # 生成 HTML + 启动服务器
    html_path = generate_note_html(filename, paragraphs, port=0)
    server = NoteServer(html_path)
    server.start()
    html_path = generate_note_html(filename, paragraphs, port=server.port)
    server.html_path = html_path

    url = f"http://localhost:{server.port}"
    self.io.tool_output(f"\n\u001b[32m✔ Opening note review...\u001b[0m")
    self.io.tool_output(f"URL: {url}")
    webbrowser.open(url)

    # 等待用户操作
    comments = server.wait_for_response(timeout=300)
    if comments is None:
        self.io.tool_output("Note cancelled or timed out.")
        return

    comment_list = comments.get("comments", [])
    if not comment_list:
        self.io.tool_output("No comments to process.")
        return

    user_msg = self._format_note_prompt(comments)
    self.io.tool_output(f"\nProcessing {len(comment_list)} comment(s)...")
    return self._generic_chat_command_for_file(
        tmp_file, user_msg, self.coder.main_model.edit_format
    )
```

---

## Files to modify

| 文件 | 修改内容 |
|------|---------|
| `lsr/commands.py` | 修改 `cmd_note`、`cmd_renote`、`_parse_and_select_sections`；新增 `_find_tex_files`、`_select_session_interactive`、`_render_session_as_html`、`_extract_paragraphs_from_temp` |

## Reuse (已有代码)

- `_parse_and_select_sections` (line 2035) — 交互选择 section 的核心逻辑，扩展无参数嗅探
- `_generic_chat_command_for_file` (line 1676) — 将 LLM 编辑聚焦到特定文件
- `_sanitize_filename` (line ~2010) — 标题 → 安全文件名
- `_format_note_prompt` — 将浏览器评论转为 LLM prompt
- `extract_text_environments` from `lsr/latex_tools` — 从 LaTeX 提取文本
- `generate_note_html` from `lsr/note_html` — 生成 HTML
- `NoteServer` from `lsr/note_server` — 本地 HTTP 服务器

## Steps

- [ ] 1. 在 `_parse_and_select_sections` 中添加 tex 文件嗅探逻辑（无参数时自动检测）
- [ ] 2. 新增 `_find_tex_files()` 辅助方法
- [ ] 3. 新增 `_select_session_interactive()` 交互选择 session 方法
- [ ] 4. 新增 `_extract_paragraphs_from_temp()` 从临时文件解析段落（提取自 `cmd_renote` 现有逻辑）
- [ ] 5. 新增 `_render_session_as_html()` 统一渲染方法
- [ ] 6. 修改 `cmd_note`：无参数时先检查 edit/note session → 嗅探 tex 文件
- [ ] 7. 修改 `cmd_renote`：搜索 `lsr_edit_*` + `lsr_note_*` session → 交互选择
- [ ] 8. 确保代码无重复，`cmd_renote` 复用 `_render_session_as_html`

## Verification

1. **tex 文件嗅探**：在无 .tex 文件的目录运行 `/note` → 提示用法；有 1 个 .tex → 自动选中；有多个 → 列出选择
2. **edit session 渲染**：先 `/edit` 创建临时文件 → `/note`（无参数）→ 列出 edit session → 选择 → 浏览器打开 HTML
3. **renote 交互**：存在多个 edit/note session 时 → `/renote` → 交互选择 → 正确渲染
4. **原有流程不受影响**：`/note <file.tex>` 仍然正常工作
5. 运行 `python -m pytest tests/` 确保无回归
