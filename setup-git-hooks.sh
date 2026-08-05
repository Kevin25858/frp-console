#!/bin/bash
# 设置 Git 提交规范的脚本

set -e

CORRECT_NAME="Kevin25858"
CORRECT_EMAIL="2802730199@qq.com"

echo "🔧 设置 Git 提交规范..."
echo ""

# 1. 设置全局 Git 配置
echo "1. 设置全局 Git 配置..."
git config --global user.name "$CORRECT_NAME"
git config --global user.email "$CORRECT_EMAIL"
echo "   ✅ 全局配置已设置: $CORRECT_NAME <$CORRECT_EMAIL>"

# 2. 设置本地 Git 配置（覆盖可能存在的错误配置）
echo "2. 设置本地 Git 配置..."
git config user.name "$CORRECT_NAME"
git config user.email "$CORRECT_EMAIL"
echo "   ✅ 本地配置已设置: $CORRECT_NAME <$CORRECT_EMAIL>"

# 3. 安装 Git 钩子
echo "3. 安装 Git 钩子..."
HOOKS_DIR=".githooks"
GIT_HOOKS_DIR=".git/hooks"

if [ -d "$HOOKS_DIR" ]; then
    for hook in "$HOOKS_DIR"/*; do
        hook_name=$(basename "$hook")
        if [ -f "$hook" ]; then
            cp "$hook" "$GIT_HOOKS_DIR/$hook_name"
            chmod +x "$GIT_HOOKS_DIR/$hook_name"
            echo "   ✅ 已安装: $hook_name"
        fi
    done
else
    echo "   ⚠️  钩子目录不存在: $HOOKS_DIR"
fi

# 4. 设置 Git 使用本地钩子目录（可选）
echo "4. 配置 Git 使用本地钩子..."
git config core.hooksPath .githooks 2>/dev/null || true

echo ""
echo "✅ 设置完成！"
echo ""
echo "当前配置："
echo "   作者名称: $(git config user.name)"
echo "   作者邮箱: $(git config user.email)"
echo ""
echo "📖 更多信息请查看: GIT_COMMIT_RULES.md"
