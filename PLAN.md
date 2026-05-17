# 修改 Aider 文件添加功能 - 始终从当前工作目录出发

## 背景

当前 Aider 的文件添加功能基于 Git 根目录来处理文件路径。当项目目录不在 Git 根目录下时，这种处理方式变得复杂且不符合某些用户的工作习惯。用户希望始终从当前工作目录（CWD）出发来处理文件路径。

## 问题分析

当前实现的问题：

1. **Git 根目录依赖**：`GitRepo` 类的 `get_tracked_files()` 方法返回的是相对于 Git 根目录的文件路径
2. **路径规范化**：`normalize_path()` 函数将路径转换为相对于 Git 根目录的路径
3. **文件添加逻辑**：`get_addable_relative_files()` 使用 Git 根目录作为参考点
4. **用户工作流限制**：当用户在子目录中工作时，需要处理复杂的相对路径
5. **命令处理**：`/add` 命令也基于 Git 根目录处理文件路径

## 修改方案

### 核心思路

保持 Git 功能（提交、差异比较等），但改变文件添加和路径处理的逻辑，使其始终从当前工作目录出发。

### 具体修改点

#### 1. 修改 `GitRepo` 类的路径处理

**文件**: `./aider/repo.py`

**修改点**:

- `normalize_path()` 方法：改为返回相对于当前工作目录的路径
- `abs_root_path()` 方法：改为基于当前工作目录
- `get_tracked_files()` 方法：返回相对于当前工作目录的路径

#### 2. 修改 `Coder` 类的文件处理逻辑

**文件**: `./aider/coders/base_coder.py`

**修改点**:

- `abs_root_path()` 方法：改为基于当前工作目录
- `get_all_relative_files()` 方法：返回相对于当前工作目录的路径
- `get_addable_relative_files()` 方法：使用当前工作目录作为参考点
- `get_rel_fname()` 方法：改为相对于当前工作目录
- `/add` 命令处理：修改为基于当前工作目录

#### 3. 添加配置选项

**文件**: `./aider/args.py`

**修改点**:

- 添加 `--cwd-relative` 命令行选项
- 默认启用，保持向后兼容

#### 4. 修改 `/add` 命令

**文件**: `./aider/commands.py`

**修改点**:

- 修改 `/add` 命令实现，使其基于当前工作目录
- 修改 `glob_filtered_to_repo` 函数，使其基于当前工作目录

### 实现细节

#### 修改 `GitRepo` 类

```python
# 在 GitRepo.__init__ 中添加
self.use_cwd = True  # 默认使用当前工作目录

# 修改 normalize_path 方法
def normalize_path(self, path):
    orig_path = path
    res = self.normalized_path.get(orig_path)
    if res:
        return res

    if self.use_cwd:
        # 使用当前工作目录作为参考点
        cwd = Path.cwd()
        try:
            path = str(Path(path).relative_to(cwd))
        except ValueError:
            # 如果路径不在当前工作目录下，保持原样
            path = str(path)
    else:
        # 保持原有逻辑，使用 Git 根目录
        path = str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))

    self.normalized_path[orig_path] = path
    return path

# 修改 abs_root_path 方法
def abs_root_path(self, path):
    if self.use_cwd:
        # 使用当前工作目录作为根目录
        res = Path.cwd() / path
    else:
        # 保持原有逻辑，使用 Git 根目录
        res = Path(self.root) / path
    return utils.safe_abs_path(res)
```

#### 修改 `Coder` 类

```python
# 在 Coder.__init__ 中添加
self.use_cwd = True  # 默认使用当前工作目录

# 修改 abs_root_path 方法
def abs_root_path(self, path):
    key = path
    if key in self.abs_root_path_cache:
        return self.abs_root_path_cache[key]

    if self.use_cwd:
        # 使用当前工作目录作为根目录
        res = Path.cwd() / path
    else:
        # 保持原有逻辑，使用 Git 根目录
        res = Path(self.root) / path

    res = utils.safe_abs_path(res)
    self.abs_root_path_cache[key] = res
    return res

# 修改 get_rel_fname 方法
def get_rel_fname(self, fname):
    try:
        if self.use_cwd:
            # 返回相对于当前工作目录的路径
            return os.path.relpath(fname, Path.cwd())
        else:
            # 保持原有逻辑，返回相对于 Git 根目录的路径
            return os.path.relpath(fname, self.root)
    except ValueError:
        return fname
```

#### 添加配置选项

```python
# 在 args.py 中添加
parser.add_argument(
    "--cwd-relative",
    action="store_true",
    default=True,
    help="Use current working directory as root for file paths instead of git root"
)

parser.add_argument(
    "--no-cwd-relative",
    action="store_false",
    dest="cwd_relative",
    help="Use git root directory as root for file paths (legacy behavior)"
)
```

### 文件修改清单

1. **`./aider/repo.py`**
   - 修改 `GitRepo.__init__`：添加 `use_cwd` 参数
   - 修改 `normalize_path()`：支持 CWD 相对路径
   - 修改 `abs_root_path()`：支持 CWD 相对路径
   - 修改 `get_tracked_files()`：返回 CWD 相对路径

2. **`./aider/coders/base_coder.py`**
   - 修改 `Coder.__init__`：添加 `use_cwd` 参数
   - 修改 `abs_root_path()`：支持 CWD 相对路径
   - 修改 `get_rel_fname()`：支持 CWD 相对路径
   - 修改 `get_all_relative_files()`：返回 CWD 相对路径

3. **`./aider/args.py`**
   - 添加 `--cwd-relative` 和 `--no-cwd-relative` 选项

4. **`./aider/commands.py`**
   - 修改 `/add` 命令实现，基于当前工作目录

### 测试计划

1. **基本功能测试**
   - 在 Git 根目录下测试文件添加
   - 在子目录下测试文件添加
   - 测试路径解析的正确性

2. **兼容性测试**
   - 测试与现有 Git 功能的兼容性
   - 测试提交、差异比较等功能
   - 测试 `.gitignore` 和 `.aiderignore` 规则

3. **用户工作流测试**
   - 测试从不同目录启动 Aider
   - 测试文件路径显示的正确性
   - 测试文件编辑和保存功能

### 验证方法

1. **功能验证**

   ```bash
   # 在 Git 根目录下测试
   cd /path/to/git/repo
   python -m aider

   # 在子目录下测试
   cd /path/to/git/repo/subdir
   python -m aider
   ```

2. **路径验证**
   - 检查添加的文件路径是否正确
   - 验证文件编辑是否应用到正确位置
   - 确认提交信息中的文件路径正确

3. **兼容性验证**
   - 测试与现有 Aider 功能的兼容性
   - 确认 Git 操作正常工作
   - 验证配置选项的正确性

## 预期效果

1. **简化工作流**：用户无需关心 Git 根目录位置
2. **直观的路径处理**：所有路径都相对于当前工作目录
3. **保持兼容性**：现有 Git 功能不受影响
4. **灵活配置**：用户可以选择使用 CWD 或 Git 根目录

## 风险与缓解

1. **路径解析错误**
   - 风险：某些路径可能无法正确解析
   - 缓解：添加详细的错误处理和用户提示

2. **Git 功能影响**
   - 风险：修改路径处理可能影响 Git 操作
   - 缓解：保持 Git 核心功能不变，只改变路径显示

3. **性能影响**
   - 风险：频繁的路径计算可能影响性能
   - 缓解：使用缓存机制，优化路径计算

## 实施步骤

### 已完成的修改

1. **修改 `GitRepo` 类** (`./aider/repo.py`)
   - 添加 `use_cwd` 参数到 `__init__` 方法
   - 修改 `normalize_path()` 方法，支持 CWD 相对路径
   - 修改 `abs_root_path()` 方法，支持 CWD 相对路径

2. **修改 `Coder` 类** (`./aider/coders/base_coder.py`)
   - 添加 `use_cwd` 参数到 `__init__` 方法
   - 修改 `abs_root_path()` 方法，支持 CWD 相对路径
   - 修改 `get_rel_fname()` 方法，支持 CWD 相对路径

3. **修改 `Commands` 类** (`./aider/commands.py`)
   - 修改 `cmd_add()` 方法，支持 CWD 相对路径
   - 修改 `glob_filtered_to_repo()` 方法，支持 CWD 相对路径

4. **修改 `args.py`** (`./aider/args.py`)
   - 添加 `--cwd-relative` 和 `--no-cwd-relative` 选项

5. **修改 `main.py`** (`./aider/main.py`)
   - 将 `args.cwd_relative` 参数传递给 `GitRepo` 和 `Coder`

### 测试验证

1. **基本功能测试**
   - 在 Git 根目录下测试文件添加 ✓
   - 在子目录下测试文件添加 ✓
   - 测试路径解析的正确性 ✓

2. **兼容性测试**
   - 测试与现有 Git 功能的兼容性 ✓
   - 测试 `/add` 命令 ✓
   - 测试 `--no-cwd-relative` 选项 ✓

3. **用户工作流测试**
   - 测试从不同目录启动 Aider ✓
   - 测试文件路径显示的正确性 ✓
   - 测试文件编辑和保存功能 ✓

### 待完成的工作

1. **文档更新**
   - 更新用户文档，说明新功能
   - 添加使用示例

2. **进一步测试**
   - 测试复杂的文件路径场景
   - 测试与现有配置文件的兼容性
   - 测试性能影响

3. **用户反馈收集**
   - 收集用户使用反馈
   - 根据反馈进行优化
