#!/bin/bash
# Beautiful-Elf 前端代码验证脚本
set -e
cd /root/.openclaw/workspace/beautiful-elf/web

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; FAIL=$((FAIL+1)); }
warn() { echo -e "${YELLOW}⚠️  WARN${NC}: $1"; WARN=$((WARN+1)); }

echo "========================================="
echo "  Beautiful-Elf 前端代码验证"
echo "========================================="
echo ""

echo "📋 1. 配置文件检查"
for f in package.json tsconfig.json vitest.config.ts eslint.config.mjs .prettierrc electron.vite.config.ts; do
  if [ -f "$f" ]; then pass "$f 存在"; else fail "$f 缺失"; fi
done
echo ""

echo "📁 2. 目录结构检查"
for d in src/main src/preload src/renderer src/renderer/components src/renderer/modules src/renderer/stores src/renderer/hooks src/renderer/services src/renderer/utils src/renderer/types src/renderer/styles src/shared; do
  if [ -d "$d" ]; then pass "目录 $d 存在"; else fail "目录 $d 缺失"; fi
done
echo ""

echo "📦 3. 功能模块目录检查"
MODULES="chat schedule clipboard snippets knowledge memory translate skills workflow subagent tools pet performance notification settings"
for mod in $MODULES; do
  MOD_DIR="src/renderer/modules/$mod"
  if [ -d "$MOD_DIR" ]; then
    if ls "$MOD_DIR"/*.tsx "$MOD_DIR"/*.ts &>/dev/null; then
      pass "模块 $mod 目录完整"
    else
      warn "模块 $mod 目录存在但可能不完整"
    fi
  else
    fail "模块 $mod 目录缺失"
  fi
done
echo ""

echo "🔤 4. 文件命名规范检查（kebab-case）"
BAD_NAMES=$(find src -name "*.tsx" -o -name "*.ts" -o -name "*.css" | grep -E '[A-Z]' | grep -v 'node_modules' | grep -v 'App.tsx' || true)
if [ -z "$BAD_NAMES" ]; then
  pass "所有文件名均为 kebab-case"
else
  fail "以下文件名包含大写字母（应为 kebab-case）："
  echo "$BAD_NAMES" | head -10
fi
echo ""

echo "🔗 5. 导入路径规范检查"
BAD_IMPORTS=$(grep -rn "from '\.\./\.\./\.\." src/renderer/ --include="*.tsx" --include="*.ts" 2>/dev/null | head -10 || true)
if [ -z "$BAD_IMPORTS" ]; then
  pass "没有过深的相对路径导入（使用 @/ 别名）"
else
  warn "发现过深的相对路径导入，建议用 @/ 别名："
  echo "$BAD_IMPORTS"
fi
echo ""

echo "📐 6. TypeScript 类型检查"
if [ -f "node_modules/.bin/tsc" ]; then
  TSC_OUT=$(npx tsc --noEmit 2>&1 || true)
  if [ -z "$TSC_OUT" ]; then
    pass "TypeScript 编译无错误"
  else
    fail "TypeScript 编译错误："
    echo "$TSC_OUT" | head -20
  fi
else
  warn "node_modules 未安装，跳过 TypeScript 类型检查（请先 npm install）"
fi
echo ""

echo "🧩 7. 公共组件检查"
for comp in page-header empty-state confirm-dialog command-palette; do
  if [ -f "src/renderer/components/${comp}.tsx" ]; then pass "公共组件 $comp 存在"; else fail "公共组件 $comp 缺失"; fi
done
if [ -f "src/renderer/components/error-boundary/global-error-boundary.tsx" ]; then pass "全局 ErrorBoundary 存在"; else fail "全局 ErrorBoundary 缺失"; fi
if [ -f "src/renderer/components/error-boundary/module-error-boundary.tsx" ]; then pass "模块级 ErrorBoundary 存在"; else fail "模块级 ErrorBoundary 缺失"; fi
for f in app-layout sidebar header status-bar; do
  if [ -f "src/renderer/components/layout/${f}.tsx" ]; then pass "布局组件 $f 存在"; else fail "布局组件 $f 缺失"; fi
done
echo ""

echo "🪝 8. 公共 Hooks 检查"
for hook in use-debounce use-auto-scroll use-local-storage use-media-query use-theme; do
  if [ -f "src/renderer/hooks/${hook}.ts" ]; then pass "Hook $hook 存在"; else fail "Hook $hook 缺失"; fi
done
echo ""

echo "🗄️ 9. Zustand Stores 检查"
for store in use-app-store use-chat-store use-command-store use-notification-store; do
  if [ -f "src/renderer/stores/${store}.ts" ]; then pass "Store $store 存在"; else fail "Store $store 缺失"; fi
done
echo ""

echo "🔧 10. 工具函数检查"
for util in cn format crypto; do
  if [ -f "src/renderer/utils/${util}.ts" ]; then pass "工具 $util 存在"; else fail "工具 $util 缺失"; fi
done
echo ""

echo "🌐 11. 服务层检查"
if [ -f "src/renderer/services/api-client.ts" ]; then pass "API 客户端存在"; else fail "API 客户端缺失"; fi
if [ -f "src/renderer/services/api-error.ts" ]; then pass "错误处理存在"; else fail "错误处理缺失"; fi
if [ -f "src/renderer/services/command-registry.ts" ]; then pass "命令注册存在"; else fail "命令注册缺失"; fi
if [ -d "src/renderer/services/websocket" ]; then pass "WebSocket 服务目录存在"; else fail "WebSocket 服务目录缺失"; fi
echo ""

echo "⚡ 12. Electron 主进程检查"
if [ -f "src/main/index.ts" ]; then pass "主进程入口存在"; else fail "主进程入口缺失"; fi
if [ -f "src/main/window-manager.ts" ]; then pass "窗口管理器存在"; else fail "窗口管理器缺失"; fi
if [ -f "src/main/ipc-handlers.ts" ]; then pass "IPC 处理器存在"; else fail "IPC 处理器缺失"; fi
if [ -f "src/main/tray.ts" ]; then pass "系统托盘存在"; else fail "系统托盘缺失"; fi
if [ -f "src/preload/index.ts" ]; then pass "预加载脚本存在"; else fail "预加载脚本缺失"; fi
echo ""

echo "🎨 13. CSS Modules 检查"
CSS_COUNT=$(find src -name "*.module.css" | wc -l)
if [ "$CSS_COUNT" -gt 0 ]; then pass "找到 $CSS_COUNT 个 CSS Modules 文件"; else warn "没有找到 CSS Modules 文件"; fi
echo ""

echo "🧪 14. 测试文件检查"
TEST_COUNT=$(find src -name "*.test.tsx" -o -name "*.test.ts" | wc -l)
if [ "$TEST_COUNT" -gt 0 ]; then
  pass "找到 $TEST_COUNT 个测试文件"
  find src -name "*.test.tsx" -o -name "*.test.ts" | sort
else
  warn "没有找到测试文件"
fi
echo ""

echo "🛣️ 15. 路由配置检查"
if grep -q "BrowserRouter" src/renderer/App.tsx; then pass "App.tsx 使用 BrowserRouter"; else fail "App.tsx 缺少 BrowserRouter"; fi
ROUTE_COUNT=$(grep -c "path=" src/renderer/App.tsx 2>/dev/null || echo 0)
if [ "$ROUTE_COUNT" -ge 15 ]; then pass "App.tsx 配置了 $ROUTE_COUNT 个路由"; else warn "App.tsx 仅配置了 $ROUTE_COUNT 个路由（期望 15 个）"; fi
echo ""

echo "========================================="
echo "  验证结果汇总"
echo "========================================="
echo -e "  ${GREEN}通过: $PASS${NC}"
echo -e "  ${RED}失败: $FAIL${NC}"
echo -e "  ${YELLOW}警告: $WARN${NC}"
echo ""
if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}🎉 所有检查通过！代码结构完整。${NC}"
  exit 0
else
  echo -e "${RED}💥 有 $FAIL 项检查失败，请修复。${NC}"
  exit 1
fi
