#!/bin/bash
# Beautiful-Elf 前端代码审查脚本
set -e

# 固定到 web 目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[✅]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠️]${NC} $1"; WARNINGS=$((WARNINGS + 1)); }
log_error() { echo -e "${RED}[❌]${NC} $1"; ERRORS=$((ERRORS + 1)); }

echo ""
echo "=========================================="
echo "  Beautiful-Elf 前端代码审查"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  工作目录: $(pwd)"
echo "=========================================="
echo ""

# 1. TypeScript 编译检查
log_info "1/6 TypeScript 编译检查..."
TSC_OUTPUT=$(npx tsc --noEmit 2>&1 || true)
# 过滤掉 baseUrl 弃用警告
TSC_ERRORS=$(echo "$TSC_OUTPUT" | grep -v "TS5101" | grep -v "Visit https" | grep -c "error TS" || true)
if [ "$TSC_ERRORS" -gt 0 ]; then
  log_error "TypeScript 编译有 $TSC_ERRORS 个错误"
  echo "$TSC_OUTPUT" | grep "error TS" | head -20
else
  log_ok "TypeScript 编译通过（仅有 baseUrl 弃用警告）"
fi
echo ""

# 2. ESLint 检查
log_info "2/6 ESLint 代码规范检查..."
ESLINT_OUTPUT=$(npx eslint src --ext .ts,.tsx 2>&1 || true)
ESLINT_ERRORS=$(echo "$ESLINT_OUTPUT" | grep -c "error" || true)
ESLINT_WARNINGS=$(echo "$ESLINT_OUTPUT" | grep -c "warning" || true)
if [ "$ESLINT_ERRORS" -gt 0 ]; then
  log_error "ESLint 有 $ESLINT_ERRORS 个错误"
  echo "$ESLINT_OUTPUT" | grep "error" | head -10
elif [ "$ESLINT_WARNINGS" -gt 0 ]; then
  log_warn "ESLint 有 $ESLINT_WARNINGS 个警告"
else
  log_ok "ESLint 检查通过"
fi
echo ""

# 3. Prettier 格式检查
log_info "3/6 Prettier 格式检查..."
PRETTIER_OUTPUT=$(npx prettier --check "src/**/*.{ts,tsx,css,json}" 2>&1 || true)
if echo "$PRETTIER_OUTPUT" | grep -q "Code style"; then
  log_warn "有文件格式不符合 Prettier 规范"
  echo "$PRETTIER_OUTPUT" | grep -E "\.(ts|tsx|css|json)$" | head -10
else
  log_ok "代码格式正确"
fi
echo ""

# 4. 检查新增文件的代码质量
log_info "4/6 新增文件代码质量检查..."
# 获取 dev 分支以来新增/修改的 TS/TSX 文件
CHANGED_FILES=$(git diff --name-only HEAD~4 2>/dev/null | grep -E '\.(tsx?)$' | grep -v 'test\.' | grep -v '__tests__' | grep -v node_modules || true)
if [ -n "$CHANGED_FILES" ]; then
  for file in $CHANGED_FILES; do
    if [ -f "$file" ]; then
      # 检查 any 类型滥用
      ANY_COUNT=$(grep -c ': any\b' "$file" 2>/dev/null || echo "0")
      if [ "$ANY_COUNT" -gt 3 ]; then
        log_warn "$file 有 $ANY_COUNT 处 any 类型，请考虑使用具体类型"
      fi
      # 检查 console.log 残留
      CONSOLE_COUNT=$(grep -c 'console\.log' "$file" 2>/dev/null || echo "0")
      if [ "$CONSOLE_COUNT" -gt 0 ]; then
        log_warn "$file 有 $CONSOLE_COUNT 处 console.log，建议移除或改用 logger"
      fi
    fi
  done
  log_ok "代码质量检查完成（共检查 $(echo "$CHANGED_FILES" | wc -l) 个文件）"
else
  log_ok "无新增文件需要检查"
fi
echo ""

# 5. 模块导出检查
log_info "5/6 模块导出检查..."
MODULES_DIR="src/renderer/modules"
MODULE_WARNINGS=0
for module_dir in "$MODULES_DIR"/*/; do
  module_name=$(basename "$module_dir")
  if [ -f "$module_dir/index.ts" ]; then
    if ! grep -q "export" "$module_dir/index.ts" 2>/dev/null; then
      log_warn "$module_name/index.ts 没有导出"
      MODULE_WARNINGS=$((MODULE_WARNINGS + 1))
    fi
  else
    log_warn "$module_name 缺少 index.ts 入口文件"
    MODULE_WARNINGS=$((MODULE_WARNINGS + 1))
  fi
done
if [ "$MODULE_WARNINGS" -eq 0 ]; then
  log_ok "模块导出检查通过"
fi
echo ""

# 6. Git 状态检查
log_info "6/6 Git 状态检查..."
CHANGED=$(git status --porcelain | wc -l)
if [ "$CHANGED" -gt 0 ]; then
  log_warn "有 $CHANGED 个未提交的文件变更"
  git status --short | head -10
else
  log_ok "工作区干净"
fi
echo ""

# 总结
echo "=========================================="
if [ $ERRORS -gt 0 ]; then
  echo -e "  ${RED}审查结果: $ERRORS 个错误, $WARNINGS 个警告${NC}"
  echo "  请修复错误后重新运行"
  exit 1
elif [ $WARNINGS -gt 0 ]; then
  echo -e "  ${YELLOW}审查结果: $WARNINGS 个警告${NC}"
  echo "  建议修复警告以提高代码质量"
  exit 0
else
  echo -e "  ${GREEN}审查结果: 全部通过 ✅${NC}"
  echo "  代码质量良好，可以提交"
  exit 0
fi
