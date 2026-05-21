# /init 命令实现总结

## 实现的功能

已成功实现 `/init` 斜杠命令，用于初始化 LaTeX 文件为最小可编译环境。

## 主要特性

### 1. 基本用法
```
/init <filename.tex>
```
- 如果文件存在，清除内容并生成最小可编译 LaTeX 模板
- 如果文件不存在，创建新文件并写入模板
- 保留一个公式、一个表格、一个图示例
- 使用占位符 `placeholder.png` 代替实际图片

### 2. 使用模板目录中的模板
```
/init <filename.tex> <template_name>
```
- 自动发现 `template/` 目录中的模板
- 提取模板的导言区（documentclass、packages）
- 保留原始标题和作者信息
- 清除内容并添加最小示例
- 支持创建新文件（包括自动创建父目录）

### 3. 帮助信息
```
/init
```
- 显示用法说明
- 列出可用的模板

## 实现细节

### 添加的方法

1. **`cmd_init(self, args)`** - 主命令方法
   - 参数验证
   - 文件路径解析
   - 自动创建父目录
   - 模板选择和应用
   - 错误处理

2. **`_discover_templates(self)`** - 模板发现
   - 扫描 `template/` 目录
   - 支持多级目录结构
   - 自动查找 `.tex` 文件

3. **`_generate_minimal_template(self)`** - 默认模板生成
   - 标准 article 文档类
   - 常用包：amsmath, graphicx, booktabs, hyperref
   - 包含公式、表格、图示例

4. **`_extract_and_minimize_template(self, template_content)`** - 模板提取
   - 提取导言区
   - 保留标题和作者
   - 添加最小内容示例

## 测试结果

✅ 帮助信息显示正常
✅ 默认模板生成正确
✅ 模板目录发现正常
✅ 模板提取功能正常
✅ 错误处理完善（非 .tex 文件）
✅ 支持创建新文件
✅ 自动创建父目录
✅ 生成的模板可编译（使用 xelatex）

## 文件修改

- `lsr/commands.py`：添加了 4 个新方法

## 使用示例

```bash
# 使用默认模板创建新文件
/init paper.tex

# 使用 wiley 模板创建新文件
/init paper.tex wiley

# 在子目录中创建文件（自动创建目录）
/init ./subdir/paper.tex wiley

# 清除现有文件内容
/init existing_paper.tex

# 查看帮助
/init
```

## 后续扩展

1. 添加更多模板到 `template/` 目录
2. 支持自定义模板路径
3. 添加模板预览功能
