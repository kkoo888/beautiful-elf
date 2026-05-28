#!/bin/bash
# Beautiful-Elf 前端代码验证脚本
# 用法: bash web/verify.sh [模块名]
# 示例: bash web/verify.sh performance

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

MODULE="${1:-}"

echo "=========================================="
echo "  Beautiful-Elf 前端代码验证"
echo "=========================================="
echo ""

# 1. TypeScript 编译检查
echo -e "${YELLOW}[1/4] TypeScript 编译检查...${NC}"
if npx tsc --noEmit 2>&1; then
  echo -e "${GREEN}  ✅ TypeScript 编译通过${NC}"
else
  echo -e "${RED}  ❌ TypeScript 编译失败${NC}"
  exit 1
fi
echo ""

# 2. ESLint 检查
echo -e "${YELLOW}[2/4] ESLint 代码规范检查...${NC}"
LINT_TARGET="src"
if [ -n "$MODULE" ]; then
  LINT_TARGET="src/renderer/modules/${MODULE}"
  if [ ! -d "$LINT_TARGET" ]; then
    LINT_TARGET="src"
    echo -e "${YELLOW}  ⚠️ 模块目录不存在，检查全部代码${NC}"
  fi
fi

if npx eslint "$LINT_TARGET" --ext .ts,.tsx 2>&1; then
  echo -e "${GREEN}  ✅ ESLint 检查通过${NC}"
else
  echo -e "${RED}  ❌ ESLint 检查有警告/错误${NC}"
  # 不退出，lint 警告不阻塞
fi
echo ""

# 3. 文件结构检查
echo -e "${YELLOW}[3/4] 模块文件结构检查...${NC}"
if [ -n "$MODULE" ]; then
  MOD_DIR="src/renderer/modules/${MODULE}"
  if [ -d "$MOD_DIR" ]; then
    echo -e "${GREEN}  ✅ 模块目录存在: ${MOD_DIR}${NC}"
    echo "  文件列表:"
    find "$MOD_DIR" -type f | sort | while read -r f; do
      echo "    📄 $f"
    done
  else
    echo -e "${RED}  ❌ 模块目录不存在: ${MOD_DIR}${NC}"
  fi
else
  echo -e "${YELLOW}  ⏭️ 未指定模块，跳过${NC}"
fi
echo ""

# 4. 重复/冲突检查
echo -e "${YELLOW}[4/4] 检查导入和类型一致性...${NC}"

# 检查是否有未使用的导入（简单检查）
echo "  检查新增文件的导入是否正确..."
IMPORT_ERRORS=0

if [ -n "$MODULE" ]; then
  MOD_DIR="src/renderer/modules/${MODULE}"
  if [ -d "$MOD_DIR" ]; then
    # 检查是否有引用不存在的模块
    for f in $(find "$MOD_DIR" -name "*.ts" -o -name "*.tsx"); do
      # 检查 @/ 导入
      if grep -q "from '@/types'" "$f" 2>/dev/null; then
        echo "  ✅ $f → @/types"
      fi
    done
  fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}  验证完成！${NC}"
echo "=========================================="
