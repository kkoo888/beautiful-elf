#!/bin/bash
# 功能开发完成后自动 review + commit + push
# 用法: ./commit-feature.sh "feat(FXX): 功能描述"

set -e

WEB_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$WEB_DIR/.." && pwd)"
cd "$WEB_DIR"

COMMIT_MSG="$1"

if [ -z "$COMMIT_MSG" ]; then
  echo "用法: $0 \"feat(FXX): 功能描述\""
  exit 1
fi

echo "🔍 运行代码审查..."
bash "$WEB_DIR/review.sh"

echo ""
echo "📦 提交代码..."
cd "$REPO_DIR"
git add -A
git commit -m "$COMMIT_MSG"

echo ""
echo "🚀 推送到远程 dev 分支..."
git push origin dev

echo ""
echo "✅ 完成: $COMMIT_MSG"
