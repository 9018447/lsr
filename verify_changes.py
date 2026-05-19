#!/usr/bin/env python
"""验证LaTeX编辑匹配优化是否成功应用"""

from pathlib import Path


def verify_changes():
    """验证修改是否正确应用"""

    editblock_path = Path("lsr/coders/editblock_coder.py")
    content = editblock_path.read_text()

    print("🔍 验证修改...")
    print("-" * 50)

    # 检查1：模糊匹配是否启用
    if "# Try fuzzy matching" in content and "replace_closest_edit_distance" in content:
        # 检查是否没有被注释掉
        lines = content.split("\n")
        fuzzy_enabled = False
        for i, line in enumerate(lines):
            if "# Try fuzzy matching" in line:
                # 检查下一行是否是代码（不是注释）
                if (
                    i + 1 < len(lines)
                    and "res = replace_closest_edit_distance" in lines[i + 1]
                ):
                    fuzzy_enabled = True
                    break

        if fuzzy_enabled:
            print("✅ 模糊匹配已启用")
        else:
            print("❌ 模糊匹配仍然被禁用")
    else:
        print("❌ 未找到模糊匹配代码")

    # 检查2：相似度阈值
    if "similarity_thresh = 0.65" in content:
        print("✅ 相似度阈值已降低到 0.65")
    elif "similarity_thresh = 0.8" in content:
        print("❌ 相似度阈值仍然是 0.8")
    else:
        print("⚠️  未找到相似度阈值设置")

    # 检查3：LaTeX预处理函数（可选）
    if "latex_normalize" in content or "latex_fuzzy_match" in content:
        print("✅ LaTeX预处理函数已添加")
    else:
        print("ℹ️  LaTeX预处理函数未添加（可选优化）")

    print("-" * 50)
    print("验证完成！")


if __name__ == "__main__":
    verify_changes()
