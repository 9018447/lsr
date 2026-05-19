#!/usr/bin/env python
"""测试LaTeX编辑匹配优化效果"""

import sys

sys.path.insert(0, ".")

from lsr.coders.editblock_coder import replace_most_similar_chunk


def test_latex_matching():
    """测试LaTeX文件的匹配效果"""

    print("🧪 测试LaTeX编辑匹配优化")
    print("=" * 60)

    test_cases = [
        {
            "name": "测试1：行尾多余空格",
            "whole": "\\begin{equation}\n  x = y\n\\end{equation}\n",
            "search": "\\begin{equation}\n  x = y  \n\\end{equation}\n",
            "replace": "\\begin{equation}\n  x = y + z\n\\end{equation}\n",
            "expected": True,
        },
        {
            "name": "测试2：前导空格差异",
            "whole": "\\section{Introduction}\nThis is text.\n",
            "search": "  \\section{Introduction}\n  This is text.\n",
            "replace": "  \\section{Introduction}\n  New text.\n",
            "expected": True,
        },
        {
            "name": "测试3：注释行差异",
            "whole": "% Comment\n\\section{Title}\nBody\n",
            "search": "\\section{Title}\nBody\n",
            "replace": "\\section{Title}\nNew Body\n",
            "expected": True,
        },
        {
            "name": "测试4：完全匹配",
            "whole": "\\begin{itemize}\n\\item A\n\\item B\n\\end{itemize}\n",
            "search": "\\begin{itemize}\n\\item A\n\\item B\n\\end{itemize}\n",
            "replace": "\\begin{itemize}\n\\item C\n\\item D\n\\end{itemize}\n",
            "expected": True,
        },
        {
            "name": "测试5：模糊匹配（相似度>65%）",
            "whole": "\\begin{document}\n\\title{My Paper}\n\\author{Author Name}\n\\end{document}\n",
            "search": "\\begin{document}\n\\title{My Paper}\n\\author{Author}\n\\end{document}\n",
            "replace": "\\begin{document}\n\\title{My Paper}\n\\author{New Author}\n\\end{document}\n",
            "expected": True,
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\n📝 {test['name']}")
        print("-" * 40)

        try:
            result = replace_most_similar_chunk(
                test["whole"], test["search"], test["replace"]
            )

            if result is not None:
                print("✅ 匹配成功")
                passed += 1
            else:
                print("❌ 匹配失败")
                failed += 1

        except Exception as e:
            print(f"❌ 错误: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_latex_matching()
    sys.exit(0 if success else 1)
