#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查 uv 是否安装
if ! command -v uv &>/dev/null; then
	echo "❌ uv 未安装，正在安装..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH="$HOME/.local/bin:$PATH"
fi

echo "uv 版本: $(uv --version)"

echo "==> 使用 uv tool 安装 aider (editable 模式)"
uv tool install -e --force "${SCRIPT_DIR}"

echo ""
echo "✅ 安装完成！直接运行 aider --help 即可使用"
