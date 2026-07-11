#!/bin/bash
# PLM System — GitHub 推送脚本
# 运行前请先在 GitHub 创建仓库: https://github.com/Gamidy/plm-system
# 或运行: gh repo create Gamidy/plm-system --public

set -e

echo "=== 推送到 GitHub ==="

# 检查远程
if ! git remote get-url origin &>/dev/null; then
    git remote add origin git@github.com:Gamidy/plm-system.git
    echo "✓ 已添加远程 origin"
else
    echo "✓ 远程已存在: $(git remote get-url origin)"
fi

# 推送
echo "推送 5 个 commits 到 main 分支..."
git push -u origin main

echo ""
echo "=== 完成 ==="
echo "仓库地址: https://github.com/Gamidy/plm-system"
