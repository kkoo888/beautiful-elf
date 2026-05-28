#!/bin/bash
# Beautiful-Elf 前端代码审查脚本
# 每次开发完一个功能后运行，检查代码质量和错误

set -e

WEB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WEB_DIR"

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
echo "=========================================="
echo ""

# 1. TypeScript 编译检查
log_info "1/7 TypeScript 编译检查..."
if npx tsc --noEmit 2>/dev/null; then
  log_ok "TypeScript 编译通过"
else
  log_error "TypeScript 编译失败"
  npx tsc --noEmit 2>&1 | head -30
fi
echo ""

# 2. ESLint 检查
log_info "2/7 ESLint 代码规范检查..."
if npx eslint src --ext .ts,.tsx --max-warnings=0 2>/dev/null; then
  log_ok "ESLint 检查通过"
else
  log_warn "ESLint 有警告或错误"
  npx eslint src --ext .ts,.tsx 2>&1 | tail -20
fi
echo ""

# 3. Prettier 格式检查
log_info "3/7 Prettier 格式检查..."
UNFORMATTED=$(npx prettier --check "src/**/*.{ts,tsx,css,json}" 2>&1 | grep -c "Code style" || true)
if [ "$UNFORMATTED" -eq 0 ]; then
  log_ok "代码格式正确"
else
  log_warn "有文件格式不符合 Prettier 规范"
  npx prettier --check "src/**/*.{ts,tsx,css,json}" 2>&1 | tail -10
fi
echo ""

# 4. 测试运行
log_info "4/7 运行单元测试..."
TEST_RESULT=$(npx vitest run --reporter=json 2>/dev/null || echo '{"testResults":[]}')
TEST_TOTAL=$(echo "$TEST_RESULT" | grep -o '"numTotalTests":[0-9]*' | cut -d: -f2 || echo "0")
TEST_FAILED=$(echo "$TEST_RESULT" | grep -o '"numFailedTests":[0-9]*' | cut -d: -f2 || echo "0")
TEST_PASSED=$(echo "$TEST_RESULT" | grep -o '"numPassedTests":[0-9]*' | cut -d: -f2 || echo "0")

if [ "$TEST_FAILED" -gt 0 ] 2>/dev/null; then
  log_error "测试失败: $TEST_FAILED/$TEST_TOTAL"
  npx vitest run 2>&1 | tail -30
else
  log_ok "测试通过: $TEST_PASSED/$TEST_TOTAL"
fi
echo ""

# 5. 依赖检查
log_info "5/7 依赖完整性检查..."
if [ -f "node_modules/.package-lock.json" ]; then
  MISSING=$(npm ls --depth=0 2>&1 | grep -c "UNMET" || true)
  if [ "$MISSING" -gt 0 ]; then
    log_warn "有未满足的依赖"
    npm ls --depth=0 2>&1 | grep "UNMET"
  else
    log_ok "依赖完整"
  fi
else
  log_warn "node_modules 不存在，请先 npm install"
fi
echo ""

# 6. 检查新增文件是否有对应的类型定义
log_info "6/7 类型定义检查..."
NEW_TS_FILES=$(git diff --name-only HEAD~1 2>/dev/null | grep -E '\.(tsx?)$' | grep -v 'test\.' | grep -v '__tests__' || true)
if [ -n "$NEW_TS_FILES" ]; then
  for file in $NEW_TS_FILES; do
    if [ -f "$file" ]; then
      # 检查是否有 any 类型滥用
      ANY_COUNT=$(grep -c ': any' "$file" 2>/dev/null || echo "0")
      if [ "$ANY_COUNT" -gt 3 ]; then
        log_warn "$file 有 $ANY_COUNT 处 any 类型，请考虑使用具体类型"
      fi
    fi
  done
  log_ok "类型定义检查完成"
else
  log_ok "无新增文件需要检查"
fi
echo ""

# 7. 组件导出检查
log_info "7/7 模块导出检查..."
MODULES_DIR="src/renderer/modules"
for module_dir in "$MODULES_DIR"/*/; do
  module_name=$(basename "$module_dir")
  if [ -f "$module_dir/index.ts" ]; then
    # 检查 index.ts 是否有默认导出
    if ! grep -q "export default\|export { default" "$module_dir/index.ts" 2>/dev/null; then
      if ! grep -q "export" "$module_dir/index.ts" 2>/dev/null; then
        log_warn "$module_name/index.ts 没有导出"
      fi
    fi
  else
    log_warn "$module_name 缺少 index.ts 入口文件"
  fi
done
log_ok "模块导出检查完成"
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
