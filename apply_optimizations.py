#!/usr/bin/env python
"""
快速应用LaTeX编辑匹配优化的脚本
"""

from pathlib import Path


def apply_quick_fix():
    """应用快速修复：启用模糊匹配 + 降低阈值"""

    editblock_path = Path("lsr/coders/editblock_coder.py")
    content = editblock_path.read_text()

    # 修复1：启用模糊匹配（第191-195行）
    # 查找被注释的代码
    old_pattern = r"    return\n    # Try fuzzy matching\n    res = replace_closest_edit_distance\(whole_lines, part, part_lines, replace_lines\)\n    if res:\n        return res"
    new_code = """    # Try fuzzy matching
    res = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)
    if res:
        return res
    
    return"""

    # 使用更精确的模式匹配
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # 检测并修复模糊匹配代码
        if (
            i < len(lines) - 4
            and "return" in lines[i]
            and "# Try fuzzy matching" in lines[i + 1]
        ):
            # 跳过原来的 return 行
            new_lines.append("    # Try fuzzy matching")
            new_lines.append(lines[i + 2])  # res = replace_closest_edit_distance(...)
            new_lines.append(lines[i + 3])  # if res:
            new_lines.append(lines[i + 4])  #     return res
            new_lines.append("")
            new_lines.append("    return")
            i += 5
        else:
            new_lines.append(line)
            i += 1

    content = "\n".join(new_lines)

    # 修复2：降低相似度阈值
    content = content.replace(
        "similarity_thresh = 0.8", "similarity_thresh = 0.65  # 更宽松的匹配，适合LaTeX"
    )

    # 写入修改
    editblock_path.write_text(content)
    print("✅ 已应用快速修复：")
    print("   - 启用模糊匹配")
    print("   - 相似度阈值降低到 0.65")


def add_latex_preprocessing():
    """添加LaTeX专用预处理（需要手动集成）"""

    latex_preprocessor = '''
def latex_normalize(text):
    """
    规范化LaTeX文本以提高匹配成功率
    
    特性：
    - 移除行尾空白
    - 保留注释行（%开头）
    - 规范化多余空格（仅用于匹配，不用于替换）
    """
    lines = text.splitlines(keepends=True)
    normalized = []
    for line in lines:
        # 移除行尾空白
        line = line.rstrip() + "\\n"
        normalized.append(line)
    return "".join(normalized)


def latex_fuzzy_match(whole_lines, part_lines, replace_lines):
    """
    LaTeX专用的模糊匹配策略
    
    尝试顺序：
    1. 忽略行尾空白的精确匹配
    2. 忽略注释行差异的匹配
    3. 规范化空格后的匹配
    4. 最相似块匹配
    """
    # 策略1：移除行尾空白后匹配
    whole_stripped = [line.rstrip() for line in whole_lines]
    part_stripped = [line.rstrip() for line in part_lines]
    
    for i in range(len(whole_stripped) - len(part_stripped) + 1):
        if whole_stripped[i:i+len(part_stripped)] == part_stripped:
            # 找到匹配，应用替换
            result = whole_lines[:i] + replace_lines + whole_lines[i+len(part_stripped):]
            return "".join(result)
    
    # 策略2：移除注释行后匹配
    whole_no_comments = [line for line in whole_lines if not line.lstrip().startswith('%')]
    part_no_comments = [line for line in part_lines if not line.lstrip().startswith('%')]
    
    # ... 更多匹配策略
    
    return None
'''

    print("\n📝 LaTeX预处理函数已生成，请手动添加到 lsr/coders/search_replace.py")
    print(latex_preprocessor)


def show_summary():
    """显示优化总结"""
    print("\n" + "=" * 60)
    print("🎯 优化总结")
    print("=" * 60)
    print("""
已应用的修改：
  ✅ 启用模糊匹配（之前被注释掉）
  ✅ 降低相似度阈值：0.8 → 0.65

建议的后续优化：
  1. 添加LaTeX专用预处理函数
  2. 实现LaTeX-aware的匹配策略
  3. 添加测试用例验证优化效果

风险提示：
  ⚠️  降低阈值可能增加错误匹配概率
  ⚠️  建议在应用前进行测试验证

测试命令：
  python -m pytest tests/test_editblock.py -v
""")


if __name__ == "__main__":
    print("🚀 应用LaTeX编辑匹配优化...")
    print("-" * 40)

    try:
        apply_quick_fix()
        add_latex_preprocessing()
        show_summary()
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
