# Beautiful-Elf 前端项目结构规范

> 版本：v1.0 | 更新日期：2026-05-29

---

## 📁 目录结构总览

```
beautiful-elf/web/
│
├── electron/                        # 🧠 Electron 主进程 + 预加载脚本（独立于渲染进程）
│   ├── main/                        # 主进程
│   │   ├── index.ts                 # 入口：创建窗口、生命周期管理
│   │   ├── window-manager.ts        # 主窗口创建/销毁/获取
│   │   ├── tray.ts                  # 系统托盘
│   │   ├── pet-window.ts            # 宠物窗口创建/销毁/获取
│   │   └── ipc-handlers/            # ⭐ 模块化 IPC 处理器
│   │       ├── index.ts             # 统一注册所有 handler
│   │       ├── window.ts            # 窗口控制（最小化/最大化/关闭）
│   │       ├── app.ts               # 应用信息（版本号等）
│   │       └── pet.ts               # 宠物窗口控制（显示/隐藏/截图传输）
│   │
│   └── preload/                     # 预加载脚本（安全桥）
│       ├── index.ts                 # 入口：contextBridge.exposeInMainWorld
│       └── api/                     # ⭐ 分层暴露给渲染进程的 API
│           ├── index.ts             # 聚合所有 API → electronAPI
│           ├── windowApi.ts         # 窗口控制 API
│           ├── appApi.ts            # 应用信息 API
│           └── petApi.ts            # 宠物窗口 API（含事件监听，返回清理函数）
│
├── public/                          # 公共静态文件（不经过构建，直接复制）
│   └── index.html
│
├── resources/                       # 应用资源（打包用）
│   └── icons/                       # 应用图标（.ico/.icns/.png）
│
├── src/
│   ├── shared/                      # 主进程 & 渲染进程共享代码
│   │   └── constants.ts             # 应用常量（API地址、WS配置、存储Key等）
│   │
│   └── renderer/                    # 🖼️ 渲染进程 — React 应用
│       ├── index.tsx                # React 入口
│       ├── App.tsx                  # 根组件（路由、Provider、全局监听）
│       │
│       ├── pages/                   # ⭐ 路由页面层（懒加载 + 错误边界）
│       │   └── index.tsx            # 所有页面组件（ChatPage, SettingsPage...）
│       │
│       ├── layouts/                 # ⭐ 布局层
│       │   └── index.ts             # 导出 MainLayout
│       │
│       ├── components/              # 通用 UI 组件（跨模块复用）
│       │   ├── layout/              # 布局组件（sidebar, header, status-bar, app-layout）
│       │   ├── error-boundary/      # 错误边界（全局 + 模块级）
│       │   ├── loading/             # 加载骨架屏
│       │   ├── command-palette.tsx   # 命令面板
│       │   ├── confirm-dialog.tsx    # 确认弹窗
│       │   ├── empty-state.tsx       # 空状态
│       │   └── page-header.tsx       # 页面标题
│       │
│       ├── modules/                 # 🧩 功能模块（业务代码核心）
│       │   └── {module-name}/       # 每个模块独立目录
│       │       ├── index.ts         # 模块入口（导出主组件）
│       │       ├── {module}-panel.tsx # 模块主面板组件
│       │       ├── components/      # 模块内组件
│       │       ├── hooks/           # 模块内 hooks
│       │       ├── services/        # 模块内 API 调用
│       │       ├── types/           # 模块内类型定义
│       │       └── __tests__/       # 模块内测试
│       │
│       ├── services/                # 🌐 全局服务层
│       │   ├── api-client.ts        # Axios 实例（拦截器、转换器）
│       │   ├── api-error.ts         # 统一错误处理
│       │   ├── endpoints.ts         # ⭐ API 端点集中管理
│       │   ├── error-reporter.ts    # 错误上报
│       │   ├── polling-registry.ts  # 轮询管理
│       │   ├── command-registry.ts  # 命令注册
│       │   └── websocket/           # WebSocket 客户端
│       │
│       ├── stores/                  # 📦 Zustand 全局状态
│       │   ├── use-app-store.ts     # 应用全局状态
│       │   ├── use-chat-store.ts    # 聊天状态
│       │   ├── use-notification-store.ts
│       │   └── use-command-store.ts
│       │
│       ├── hooks/                   # 🪝 全局共享 hooks
│       │   ├── index.ts             # 统一导出
│       │   ├── use-electron-api.ts  # ⭐ Electron API 调用封装
│       │   ├── use-ipc.ts           # Zod 校验的 IPC 调用（高级用法）
│       │   ├── use-debounce.ts
│       │   ├── use-local-storage.ts
│       │   ├── use-media-query.ts
│       │   ├── use-theme.ts
│       │   └── use-theme-persist.ts
│       │
│       ├── types/                   # 📝 全局类型定义
│       │   ├── index.ts             # 统一导出
│       │   ├── common.ts            # 通用类型
│       │   ├── api.ts               # API 响应类型
│       │   └── electron.d.ts        # ⭐ Electron API 类型声明
│       │
│       ├── utils/                   # 🔧 工具函数
│       │   ├── index.ts             # 统一导出
│       │   ├── cn.ts                # className 合并
│       │   ├── format.ts            # 格式化
│       │   ├── crypto.ts            # 加密
│       │   └── undo-toast.ts        # 撤销提示
│       │
│       ├── assets/                  # 📦 静态资源（经过构建处理）
│       │   ├── images/              # 图片
│       │   ├── fonts/               # 字体
│       │   └── styles/              # 额外样式
│       │
│       └── styles/                  # 🎨 全局样式
│           ├── global.css           # 全局 CSS
│           └── theme-provider.tsx   # 主题 Provider
│
├── tests/                           # 测试目录
│
├── .env                             # 环境变量（默认值）
├── .gitignore                       # Git 忽略规则
├── electron-builder.json            # Electron 打包配置
├── electron.vite.config.ts          # Electron-Vite 构建配置
├── tsconfig.json                    # TypeScript 配置
└── package.json
```

---

## 📐 放置规则

### 1. Electron 主进程代码 → `electron/`

| 文件类型 | 放哪里 | 示例 |
|---------|--------|------|
| 主进程入口 | `electron/main/index.ts` | 应用生命周期 |
| 窗口管理 | `electron/main/window-manager.ts` | 创建/销毁窗口 |
| 系统托盘 | `electron/main/tray.ts` | 托盘菜单 |
| IPC 处理器 | `electron/main/ipc-handlers/{module}.ts` | 按功能模块拆分 |
| 预加载 API | `electron/preload/api/{module}Api.ts` | 按功能模块拆分 |

**规则：**
- IPC handlers **必须按模块拆分**，不要放在一个文件里
- 每个 handler 文件导出一个 `register{Module}Handlers()` 函数
- `ipc-handlers/index.ts` 统一注册所有 handler
- preload API **必须返回清理函数**（用于事件监听）
- 新增 IPC 通道时，**主进程 handler 和 preload API 必须同步添加**

### 2. 功能模块 → `src/renderer/modules/{module-name}/`

| 文件类型 | 放哪里 | 说明 |
|---------|--------|------|
| 模块主面板 | `{module}-panel.tsx` | 路由直接加载的组件 |
| 子组件 | `components/` | 模块内部使用的组件 |
| 自定义 hooks | `hooks/` | 模块内部的 hooks |
| API 调用 | `services/` | 调用后端接口 |
| 类型定义 | `types/` | 模块专用类型 |
| 测试 | `__tests__/` | 模块单元测试 |
| 模块入口 | `index.ts` | 导出主组件 |

**规则：**
- 模块之间**禁止直接引用**，必须通过全局 services/stores/hooks
- 模块内 `services/` 只放该模块专用的 API 调用
- 新模块**必须创建完整的子目录结构**

### 3. API 端点管理 → `src/renderer/services/endpoints.ts`

| 类型 | 放哪里 | 说明 |
|------|--------|------|
| 全局 API 端点 | `services/endpoints.ts` | 集中管理所有端点常量 |
| API 客户端 | `services/api-client.ts` | Axios 实例、拦截器 |
| 模块内 API 调用 | `modules/{module}/services/` | 使用 endpoints 常量 |

**规则：**
- 所有 API 端点**必须在 `endpoints.ts` 中定义**，禁止硬编码
- 端点按模块分组，使用 `as const` 断言
- 动态端点使用函数：`(id: string) => \`${API_PREFIX}/xxx/${id}\``
- 模块内 API 文件**必须引用 `endpoints.ts` 中的常量**

```typescript
// ✅ 正确
import { CHAT_ENDPOINTS } from '@/services/endpoints'
const resp = await apiClient.get(CHAT_ENDPOINTS.CONVERSATIONS)

// ❌ 错误
const resp = await apiClient.get('/api/v1/chat/conversations')
```

### 4. Electron API 调用 → `useElectronApi` hook

| 场景 | 用什么 | 说明 |
|------|--------|------|
| 组件内调用 Electron | `useElectronApi()` hook | 类型安全 + 环境检测 |
| 高级 IPC（Zod 校验） | `useIPC()` hook | 需要运行时类型校验时 |

**规则：**
- **禁止直接调用 `window.electronAPI`**，必须通过 `useElectronApi` hook
- hook 自动处理非 Electron 环境的降级
- 事件监听方法**必须返回清理函数**，组件 useEffect 中**必须调用清理**

```typescript
// ✅ 正确
const { pet: petApi, isElectron } = useElectronApi()
useEffect(() => {
  if (!isElectron) return
  const cleanup = petApi.onScreenshotUpdate(setScreenshot)
  return () => cleanup()
}, [isElectron, petApi])

// ❌ 错误
useEffect(() => {
  window.electronAPI?.pet?.onScreenshotUpdate(setScreenshot) // 无清理！
}, [])
```

### 5. 路由页面 → `src/renderer/pages/`

**规则：**
- 每个路由对应一个页面组件
- 页面组件**必须用 `PageSuspense` 包裹**（懒加载 + 错误边界）
- 页面组件只做组合，业务逻辑放在模块内
- 新增页面后**必须在 `App.tsx` 中添加路由**

### 6. 全局状态 → `src/renderer/stores/`

**规则：**
- 按功能域拆分 store，不要一个大 store
- 使用 Zustand 的 `selector` 模式避免不必要的重渲染
- store 文件命名：`use-{domain}-store.ts`

### 7. 工具函数 → `src/renderer/utils/`

**规则：**
- 纯函数，无副作用
- 按功能拆分文件
- `index.ts` 统一导出

### 8. 静态资源

| 类型 | 放哪里 | 说明 |
|------|--------|------|
| 构建处理的资源 | `src/renderer/assets/` | 图片、字体、额外样式 |
| 不构建的静态文件 | `public/` | favicon、index.html |
| 应用打包资源 | `resources/` | 应用图标、安装背景 |

---

## 🔌 新增功能 Checklist

开发新功能时，按此清单逐项完成：

### 新增模块
- [ ] 创建 `modules/{name}/` 目录及子目录
- [ ] 创建 `{name}-panel.tsx` 主面板
- [ ] 创建 `index.ts` 入口
- [ ] 在 `pages/index.tsx` 中添加页面组件
- [ ] 在 `App.tsx` 中添加路由
- [ ] 在 `services/endpoints.ts` 中添加 API 端点

### 新增 Electron API
- [ ] 在 `electron/main/ipc-handlers/` 中添加 handler 文件
- [ ] 在 `ipc-handlers/index.ts` 中注册
- [ ] 在 `electron/preload/api/` 中添加 API 文件
- [ ] 在 `preload/api/index.ts` 中聚合
- [ ] 在 `types/electron.d.ts` 中添加类型声明
- [ ] 在 `hooks/use-electron-api.ts` 中添加封装
- [ ] 事件监听方法**必须返回清理函数**

### 新增全局 Hook
- [ ] 创建 `hooks/use-{name}.ts`
- [ ] 在 `hooks/index.ts` 中导出

### 新增全局 Store
- [ ] 创建 `stores/use-{name}-store.ts`

---

## 🚫 常见错误

| 错误做法 | 正确做法 |
|---------|---------|
| 模块 A 直接 import 模块 B 的组件 | 通过全局 services/stores 通信 |
| API 端点硬编码在模块内 | 在 `services/endpoints.ts` 统一定义 |
| 直接调用 `window.electronAPI` | 使用 `useElectronApi()` hook |
| IPC handler 全写一个文件 | 按模块拆分到 `ipc-handlers/` |
| preload API 不返回清理函数 | 事件监听必须返回 `() => removeListener()` |
| useEffect 不清理 IPC 监听器 | 必须在 return 中调用 cleanup |
| `useCallback` 嵌套在 `useMemo` 里 | 违反 Rules of Hooks，用普通函数替代 |
| 新增 IPC 只改主进程不改 preload | 主进程和 preload **必须同步修改** |

---

## 🏗️ 技术栈

| 类别 | 技术 |
|------|------|
| 桌面框架 | Electron 41 |
| 构建工具 | electron-vite 3 |
| 前端框架 | React 19 |
| UI 组件库 | Ant Design 6 |
| 状态管理 | Zustand + TanStack React Query |
| 路由 | React Router v7 |
| 表单 | React Hook Form + Zod |
| 代码编辑 | CodeMirror |
| 工作流可视化 | ReactFlow |
| HTTP 客户端 | Axios |
| 语言 | TypeScript 6 |
| 打包 | electron-builder |
