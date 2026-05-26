# Beautiful-Elf 前端独立开发拆分方案

> 按「可独立开发、不依赖后端服务」原则拆分，每个块可单独完成 UI + 交互 + 本地状态。
> 后端依赖仅限 API 调用部分，用 mock 数据替代即可。

---

## 📋 拆分总览

| 编号 | 开发块 | 依赖后端 | 依赖本地服务 | 复杂度 | 预估工时 |
|------|--------|---------|-------------|--------|---------|
| F01 | 项目脚手架 & 工程化 | ❌ | ❌ | ⭐⭐ | 0.5d |
| F02 | 全局布局 & 侧边栏导航 | ❌ | ❌ | ⭐⭐ | 0.5d |
| F03 | 主题系统 | ❌ | ❌ | ⭐⭐ | 0.5d |
| F04 | 全局状态管理 & 错误处理 | ❌ | ❌ | ⭐⭐ | 1d |
| F05 | 命令面板 | ❌ | ❌ | ⭐⭐ | 1d |
| F06 | 聊天面板 | ✅ (mock) | ❌ | ⭐⭐⭐ | 2d |
| F07 | 日程模块 | ✅ (mock) | ❌ | ⭐⭐⭐ | 1.5d |
| F08 | 剪贴板模块 | ❌ | ❌ | ⭐⭐ | 1d |
| F09 | 代码片段模块 | ❌ | ❌ | ⭐⭐ | 1d |
| F10 | 知识库模块 | ✅ (mock) | ❌ | ⭐⭐⭐ | 1.5d |
| F11 | 记忆模块 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F12 | 翻译模块 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F13 | 技能管理面板 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F14 | 工作流模块 | ✅ (mock) | ❌ | ⭐⭐⭐⭐ | 2d |
| F15 | 子代理面板 | ✅ (mock) | ❌ | ⭐⭐⭐ | 1.5d |
| F16 | 工具管理面板 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F17 | 3D 桌面宠物窗口 | ❌ | ❌ | ⭐⭐⭐⭐⭐ | 3d |
| F18 | 宠物主窗口面板 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F19 | 性能监控面板 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F20 | 通知中心 | ✅ (mock) | ❌ | ⭐⭐ | 1d |
| F21 | 设置系统 | ✅ (mock) | ❌ | ⭐⭐⭐ | 1.5d |
| F22 | 文件预览 | ❌ | ❌ | ⭐⭐ | 1d |
| F23 | OCR 截图识别 | ❌ | ❌ | ⭐⭐ | 1d |
| F24 | 截图选区 | ❌ | Electron | ⭐⭐⭐ | 1d |
| F25 | 系统托盘 & 全局快捷键 | ❌ | Electron | ⭐ | 0.5d |
| F26 | 离线存储 & 网络状态 | ❌ | ❌ | ⭐⭐ | 1d |
| F27 | 多窗口 IPC 通信 | ❌ | Electron | ⭐⭐⭐ | 1d |
| F28 | WebSocket 通信层 | ✅ | ❌ | ⭐⭐⭐ | 1d |
| F29 | AI 护栏 & 反馈系统 | ✅ (mock) | ❌ | ⭐⭐ | 1d |

**总计：约 33 个工作日**

---

## 📦 F01 项目脚手架 & 工程化

**不依赖任何后端服务，纯本地开发环境**

### 包含内容

| 项目 | 说明 |
|------|------|
| electron-vite 初始化 | 主进程 + 渲染进程 + 预加载脚本 |
| TypeScript 配置 | tsconfig.json，路径别名 @/ |
| React 19 引入 | 包含 JSX 配置 |
| Ant Design v6 引入 | 全局 ConfigProvider |
| ESLint + Prettier | 代码规范 |
| Husky + lint-staged + commitlint | Git hooks |
| 目录结构搭建 | 按模块划分 |
| Vitest 测试框架 | 单元测试环境 |

### 目录结构

```
src/
├── main/                    # Electron 主进程
│   ├── index.ts
│   ├── window-manager.ts   # 窗口管理
│   ├── tray.ts             # 系统托盘
│   └── ipc-handlers.ts     # IPC 处理
├── preload/                 # 预加载脚本
│   └── index.ts
├── renderer/                # 渲染进程 (React)
│   ├── App.tsx
│   ├── index.tsx
│   ├── assets/
│   ├── components/          # 通用组件
│   │   ├── error-boundary/
│   │   ├── loading/
│   │   └── layout/
│   ├── modules/             # 功能模块
│   │   ├── chat/
│   │   ├── schedule/
│   │   ├── clipboard/
│   │   ├── snippets/
│   │   ├── knowledge/
│   │   ├── memory/
│   │   ├── translate/
│   │   ├── skills/
│   │   ├── workflow/
│   │   ├── subagent/
│   │   ├── tools/
│   │   ├── pet/
│   │   ├── performance/
│   │   ├── notification/
│   │   └── settings/
│   ├── stores/              # Zustand stores
│   ├── hooks/               # 自定义 hooks
│   ├── services/            # API 调用层
│   ├── utils/               # 工具函数
│   ├── types/               # TypeScript 类型
│   └── styles/              # 全局样式
└── shared/                  # 主进程 & 渲染进程共享
    └── constants.ts
```

### 验收标准

- [ ] `npm run dev` 启动 Electron 窗口
- [ ] TypeScript 编译无报错
- [ ] ESLint + Prettier 正常工作
- [ ] Git commit 走 Husky 钩子
- [ ] Vitest 可运行测试

---

## 📦 F02 全局布局 & 侧边栏导航

**纯 UI 组件，不依赖任何数据**

### 包含内容

| 组件 | 说明 |
|------|------|
| `AppLayout` | Ant Design Layout：侧边栏 + 头部 + 内容区 |
| `Sidebar` | 侧边栏导航菜单，按分组折叠 |
| `Header` | 顶部栏：当前模块标题 + 全局操作 |
| `ContentArea` | 主内容区，路由切换 |
| `StatusBar` | 底部状态栏：网络状态 + 撤销提示 |

### 侧边栏分组结构

```
📁 核心
  💬 对话 (默认首页)
  📅 日程
  📋 剪贴板
  💻 代码片段

📁 知识 & AI
  📚 知识库
  🧠 记忆
  🌐 翻译
  🔧 技能

📁 自动化
  ⚙️ 工作流
  🤖 子代理
  🔌 工具管理

📁 系统
  🐾 宠物
  📊 性能监控
  🔔 通知
  ⚙️ 设置
```

### 路由设计

```typescript
// React Router 路由表
const routes = [
  { path: '/', element: <ChatPanel /> },
  { path: '/schedule', element: <SchedulePanel /> },
  { path: '/clipboard', element: <ClipboardPanel /> },
  { path: '/snippets', element: <SnippetsPanel /> },
  { path: '/knowledge', element: <KnowledgePanel /> },
  { path: '/memory', element: <MemoryPanel /> },
  { path: '/translate', element: <TranslatePanel /> },
  { path: '/skills', element: <SkillsPanel /> },
  { path: '/workflow', element: <WorkflowPanel /> },
  { path: '/subagent', element: <SubagentPanel /> },
  { path: '/tools', element: <ToolsPanel /> },
  { path: '/pet', element: <PetPanel /> },
  { path: '/performance', element: <PerformancePanel /> },
  { path: '/notification', element: <NotificationPanel /> },
  { path: '/settings', element: <SettingsPanel /> },
];
```

### 验收标准

- [ ] 侧边栏分组可折叠/展开
- [ ] 点击菜单切换内容区
- [ ] 当前路由高亮
- [ ] 响应式：窄屏侧边栏收起
- [ ] 底部状态栏常驻

---

## 📦 F03 主题系统

**纯前端，通过 Ant Design ConfigProvider 实现**

### 包含内容

| 功能 | 说明 |
|------|------|
| 内置主题 | 明亮、暗色、高对比度 |
| 主题切换 | 一键切换，Zustand 持久化 |
| Design Token | 自定义 Ant Design token |
| 主题导入/导出 | JSON 文件上传下载 |
| 启动恢复 | 从本地存储读取上次主题 |

### 主题 Token 定义

```typescript
interface ThemeTokens {
  colorPrimary: string;
  colorBgBase: string;
  colorTextBase: string;
  borderRadius: number;
  fontSize: number;
  // ...更多 token
}

// 内置主题
const themes: Record<string, ThemeTokens> = {
  light: { colorPrimary: '#1677ff', colorBgBase: '#ffffff', ... },
  dark:  { colorPrimary: '#1677ff', colorBgBase: '#141414', ... },
  highContrast: { colorPrimary: '#0000ff', colorBgBase: '#000000', ... },
};
```

### 验收标准

- [ ] 三种内置主题可切换
- [ ] 暗色模式正常显示
- [ ] 主题选择持久化（重启恢复）
- [ ] 可导出/导入主题 JSON

---

## 📦 F04 全局状态管理 & 错误处理

**纯前端架构层，不依赖后端**

### 包含内容

| 模块 | 说明 |
|------|------|
| Zustand stores | 各模块状态 store |
| ErrorBoundary | 应用级 + 模块级 |
| 全局错误捕获 | unhandledrejection |
| Loading 状态 | 面板级/数据级/操作级 |
| 网络状态监听 | navigator.onLine + 事件 |

### Zustand Store 划分

```typescript
// 每个模块独立 store
useChatStore        // 聊天状态
useScheduleStore    // 日程状态
useClipboardStore   // 剪贴板状态
useSnippetsStore    // 代码片段状态
useKnowledgeStore   // 知识库状态
useMemoryStore      // 记忆状态
useTranslateStore   // 翻译状态
useSkillsStore      // 技能状态
useWorkflowStore    // 工作流状态
useSubagentStore    // 子代理状态
useToolsStore       // 工具状态
usePetStore         // 宠物状态
usePerformanceStore // 性能监控状态
useNotificationStore // 通知状态
useSettingsStore    // 设置状态
useAppStore         // 全局状态（主题、网络、侧边栏）
```

### ErrorBoundary 层级

```tsx
<App>
  <ErrorBoundary fallback={<GlobalErrorCard />}>
    <AppLayout>
      <ErrorBoundary fallback={<ModuleErrorCard />}>
        <Outlet />  {/* 路由内容 */}
      </ErrorBoundary>
    </AppLayout>
  </ErrorBoundary>
</App>
```

### 验收标准

- [ ] 全局异常显示错误卡片
- [ ] 模块异常独立处理不影响其他模块
- [ ] 网络断开底部状态栏变红
- [ ] Zustand store 可正常读写

---

## 📦 F05 命令面板

**纯前端，全局覆盖层组件**

### 包含内容

| 功能 | 说明 |
|------|------|
| 快捷键唤起 | Ctrl+K 全局触发 |
| AutoComplete 搜索 | 输入关键词匹配命令 |
| 智能排序 | 精确 > 前缀 > 模糊，同级按频率 |
| 动态注册 | 各模块可注册自己的命令 |
| 最近使用 | 优先展示最近用过的命令 |

### 命令注册表

```typescript
interface Command {
  id: string;
  name: string;           // 显示名称
  keywords: string[];     // 搜索关键词
  icon: React.ReactNode;  // 图标
  module: string;         // 所属模块
  action: () => void;     // 执行函数
  useCount: number;       // 使用次数
  lastUsedAt?: number;    // 最后使用时间
}
```

### 排序规则

```
输入关键词 → 匹配命令列表 → 排序:
  1. 精确匹配 (命令名完全匹配) → 最前
  2. 前缀匹配 (命令名以关键词开头)
  3. 模糊匹配 (包含关键词)
  4. 同匹配度内按使用频率降序
  5. 同频率按最近使用时间降序
  最多显示 20 条结果
```

### 验收标准

- [ ] Ctrl+K 唤起命令面板
- [ ] 输入关键词实时过滤
- [ ] 选中命令可执行
- [ ] 使用频率影响排序
- [ ] Esc 关闭面板

---

## 📦 F06 聊天面板

**核心模块，UI 先行，API 用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 消息列表 | Ant Design List + 虚拟滚动 (react-window) |
| 消息气泡 | Markdown 渲染 (react-markdown + remark-gfm) |
| 代码块高亮 | prismjs 语法高亮 |
| 输入框 | 多行输入 + 快捷键发送 |
| 流式显示 | 逐字展示动画（mock 阶段模拟） |
| 推理深度切换 | Segmented：快速 / 深度 / 全面 |
| AI 反馈 | 👍👎 按钮 + 原因标签 |
| 快速回答标识 | ⚡ 标记缓存回答 |
| 会话管理 | 新建 / 切换 / 删除会话 |
| 自动滚动 | 新消息自动滚到底部 |
| 消息操作 | 复制 / 重新生成 / 删除 |

### 组件拆分

```
chat/
├── ChatPanel.tsx              # 主面板容器
├── MessageList.tsx            # 消息列表（虚拟滚动）
├── MessageBubble.tsx          # 单条消息气泡
├── MarkdownRenderer.tsx       # Markdown 渲染
├── CodeBlock.tsx              # 代码块（语法高亮 + 复制）
├── ChatInput.tsx              # 输入框
├── ReasoningDepthSwitch.tsx   # 推理深度切换
├── FeedbackButtons.tsx        # 👍👎 反馈
├── ConversationList.tsx       # 会话列表侧栏
└── QuickAnswerBadge.tsx       # ⚡ 快速回答标识
```

### Mock 数据

```typescript
const mockMessages: ChatMessage[] = [
  { id: '1', role: 'user', content: '你好', createdAt: Date.now() },
  { id: '2', role: 'assistant', content: '**你好！** 有什么可以帮你的？', createdAt: Date.now() + 1000 },
  { id: '3', role: 'assistant', content: '```python\nprint("hello")\n```', createdAt: Date.now() + 2000 },
];
```

### 验收标准

- [ ] 消息列表虚拟滚动流畅
- [ ] Markdown 正常渲染（标题/列表/代码/链接）
- [ ] 代码块语法高亮 + 一键复制
- [ ] 推理深度可切换
- [ ] 新消息自动滚动
- [ ] 长列表 1000+ 条消息不卡顿

---

## 📦 F07 日程模块

**UI + 交互，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 日历视图 | @ant-design/calendar 月/周/日 |
| 日程 CRUD | 创建 / 编辑 / 删除日程 |
| 表单校验 | React Hook Form + Zod |
| 全天事件 | 支持全天事件标记 |
| 提前提醒 | 设置提醒时间（分钟） |
| 颜色分类 | 不同颜色标记不同类型 |
| 重复事件 | 每天 / 每周 / 每月 |

### 组件拆分

```
schedule/
├── SchedulePanel.tsx      # 主面板
├── CalendarView.tsx       # 日历视图
├── ScheduleForm.tsx       # 创建/编辑表单
├── ScheduleCard.tsx       # 日程卡片
├── ScheduleDetail.tsx     # 日程详情弹窗
└── ReminderSettings.tsx   # 提醒设置
```

### 表单 Schema

```typescript
const scheduleSchema = z.object({
  title: z.string().min(1, '标题不能为空').max(100),
  description: z.string().max(500).optional(),
  startTime: z.date(),
  endTime: z.date(),
  isAllDay: z.boolean().default(false),
  reminderMinutes: z.number().min(0).max(1440),
  color: z.string().optional(),
  repeat: z.enum(['none', 'daily', 'weekly', 'monthly']).default('none'),
});
```

### 验收标准

- [ ] 月/周/日视图可切换
- [ ] 点击日期创建日程
- [ ] 表单校验完整
- [ ] 日程卡片可编辑/删除
- [ ] 颜色分类显示

---

## 📦 F08 剪贴板模块

**纯前端，Electron 原生剪贴板 API**

### 包含内容

| 功能 | 说明 |
|------|------|
| 剪贴板监听 | clipboard-event-emitter 事件驱动 |
| 历史列表 | 虚拟滚动，右键菜单 |
| 搜索过滤 | 按内容关键词搜索 |
| 固定 (Pin) | 固定重要内容不被清理 |
| 一键复制 | 点击条目复制到剪贴板 |
| 删除 | 右键删除单条 |

### 组件拆分

```
clipboard/
├── ClipboardPanel.tsx     # 主面板
├── ClipboardList.tsx      # 历史列表（虚拟滚动）
├── ClipboardItem.tsx      # 单条内容
├── ClipboardSearch.tsx    # 搜索栏
└── ContextMenu.tsx        # 右键菜单
```

### 本地存储

```typescript
// 剪贴板数据存本地（IndexedDB 或 localStorage）
interface ClipboardItem {
  id: string;
  content: string;
  type: 'text' | 'image' | 'file';
  pinned: boolean;
  createdAt: number;
}
```

### 验收标准

- [ ] 监听剪贴板变化自动记录
- [ ] 列表虚拟滚动流畅
- [ ] 搜索实时过滤
- [ ] 固定条目不被清理
- [ ] 右键菜单操作

---

## 📦 F09 代码片段模块

**纯前端，react-codemirror 编辑器**

### 包含内容

| 功能 | 说明 |
|------|------|
| 代码编辑器 | react-codemirror (CodeMirror 6) |
| 语法高亮 | 100+ 语言支持 |
| 标签管理 | Ant Design Tag + Select 多选 |
| 使用统计 | 本地记录使用次数，高频靠前 |
| CRUD | 创建 / 编辑 / 删除片段 |
| 搜索 | 按标题 / 标签 / 代码内容搜索 |

### 组件拆分

```
snippets/
├── SnippetsPanel.tsx      # 主面板
├── SnippetEditor.tsx      # CodeMirror 编辑器
├── SnippetList.tsx        # 片段列表
├── SnippetCard.tsx        # 片段卡片
├── TagManager.tsx         # 标签管理
└── SnippetSearch.tsx      # 搜索
```

### 验收标准

- [ ] CodeMirror 编辑器正常显示
- [ ] 语法高亮正确
- [ ] 标签可增删筛选
- [ ] 使用频率排序
- [ ] 一键复制代码

---

## 📦 F10 知识库模块

**UI 先行，文档导入/展示用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 文档列表 | Ant Design Table，按类型/时间筛选 |
| 文件上传 | 支持 PDF/DOCX/MD/TXT/JSON/CSV/YAML/HTML/XML/ZIP |
| 上传进度 | Ant Design Progress 进度条 |
| 文档删除 | 软删除 + 回收站 |
| 文档导出 | JSON 格式导出 |
| 文档预览 | 点击预览文档内容 |

### 组件拆分

```
knowledge/
├── KnowledgePanel.tsx     # 主面板
├── DocumentTable.tsx      # 文档列表表格
├── UploadZone.tsx         # 拖拽上传区域
├── UploadProgress.tsx     # 上传进度
├── DocumentPreview.tsx    # 文档预览
├── RecycleBin.tsx         # 回收站
└── ExportButton.tsx       # 导出按钮
```

### 支持文件类型

```typescript
const SUPPORTED_FILE_TYPES = [
  '.pdf', '.docx', '.md', '.txt', '.json',
  '.csv', '.yaml', '.yml', '.html', '.xml', '.zip',
];

const FILE_TYPE_ICONS: Record<string, string> = {
  '.pdf': '📄', '.docx': '📝', '.md': '📑',
  '.txt': '📃', '.json': '🔧', '.csv': '📊',
  '.yaml': '⚙️', '.html': '🌐', '.xml': '📋', '.zip': '📦',
};
```

### 验收标准

- [ ] 文件拖拽上传
- [ ] 支持的文件类型显示图标
- [ ] 上传进度条
- [ ] 删除后进入回收站
- [ ] 可恢复误删文档

---

## 📦 F11 记忆模块

**UI 先行，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 记忆列表 | 长期记忆条目展示 |
| 语义搜索 | 搜索输入框 + 结果列表 |
| 记忆详情 | 展开查看完整内容 |
| 记忆来源 | 关联的会话/对话 |
| 时间线视图 | 按时间排列 |

### 组件拆分

```
memory/
├── MemoryPanel.tsx        # 主面板
├── MemoryList.tsx         # 记忆列表
├── MemoryCard.tsx         # 记忆卡片
├── MemorySearch.tsx       # 语义搜索
├── MemoryDetail.tsx       # 记忆详情
└── MemoryTimeline.tsx     # 时间线视图
```

### 验收标准

- [ ] 记忆列表分页展示
- [ ] 搜索框输入触发过滤
- [ ] 记忆卡片可展开详情
- [ ] 时间线视图切换

---

## 📦 F12 翻译模块

**UI 先行，翻译逻辑 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 语言选择 | 源语言 / 目标语言下拉 |
| 原文/译文对照 | 左右分栏展示 |
| 翻译模式 | 通用翻译 / 小希翻译（术语+RAG） |
| 翻译历史 | 历史记录列表 |
| 收藏 | 收藏常用翻译 |
| 一键复制 | 复制译文 |

### 组件拆分

```
translate/
├── TranslatePanel.tsx     # 主面板
├── LanguageSelector.tsx   # 语言选择器
├── TranslationView.tsx    # 原文/译文对照
├── TranslationMode.tsx    # 翻译模式切换
├── TranslationHistory.tsx # 翻译历史
└── FavoriteList.tsx       # 收藏列表
```

### 验收标准

- [ ] 语言选择可切换
- [ ] 原文/译文左右对照
- [ ] 翻译模式可切换
- [ ] 历史记录可查看
- [ ] 收藏功能正常

---

## 📦 F13 技能管理面板

**UI 先行，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 技能列表 | Ant Design Table |
| 启用/禁用 | Switch 开关 |
| 技能详情 | 描述、版本、依赖、触发词 |
| 技能炼化 | 点击"炼化"触发优化建议 |
| 链式配置 | 配置技能调用链 |
| 安装/卸载 | 从本地或远程安装 |

### 组件拆分

```
skills/
├── SkillsPanel.tsx        # 主面板
├── SkillsTable.tsx        # 技能列表表格
├── SkillDetail.tsx        # 技能详情
├── SkillToggle.tsx        # 启用/禁用开关
├── RefineButton.tsx       # 炼化按钮
├── ChainConfig.tsx        # 链式配置
└── InstallDialog.tsx      # 安装对话框
```

### 验收标准

- [ ] 技能列表展示完整信息
- [ ] 可启用/禁用技能
- [ ] 炼化按钮可触发
- [ ] 链式配置可编辑

---

## 📦 F14 工作流模块

**最复杂的模块之一，UI 先行**

### 包含内容

| 功能 | 说明 |
|------|------|
| DAG 编辑器 | 可视化工作流节点编辑 |
| 节点拖拽 | 拖拽添加/移动节点 |
| 连线 | 节点间连线定义依赖 |
| 节点配置 | 选中节点配置参数 |
| 模板系统 | 预置工作流模板 |
| 运行监控 | 实时展示节点状态 |
| 运行历史 | 历史运行记录 |

### 组件拆分

```
workflow/
├── WorkflowPanel.tsx      # 主面板
├── DagEditor.tsx          # DAG 可视化编辑器
├── WorkflowNode.tsx       # 工作流节点组件
├── NodeConfig.tsx         # 节点配置面板
├── ConnectionLine.tsx     # 连线组件
├── TemplateList.tsx       # 模板列表
├── RunMonitor.tsx         # 运行监控
├── RunHistory.tsx         # 运行历史
└── NodeToolbar.tsx        # 节点工具栏
```

### DAG 编辑器技术选型

| 方案 | 优点 | 缺点 |
|------|------|------|
| React Flow | 成熟、社区活跃、功能全 | 包体积较大 |
| 自研 Canvas | 完全可控 | 开发成本高 |

**推荐：React Flow**（成熟方案，减少开发量）

### 验收标准

- [ ] 可拖拽添加节点
- [ ] 节点间可连线
- [ ] 选中节点可配置参数
- [ ] 预置模板可一键创建
- [ ] 运行状态实时展示

---

## 📦 F15 子代理面板

**UI 先行，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 运行列表 | Ant Design Table，展示运行中子代理 |
| 状态标签 | 运行中 / 暂停 / 已完成 / 失败 |
| Timeline | Ant Design Timeline 展示执行步骤 |
| 终止按钮 | 单个终止 + 一键全部终止 |
| 实时更新 | WebSocket 推送状态变更 |

### 组件拆分

```
subagent/
├── SubagentPanel.tsx      # 主面板
├── SubagentTable.tsx      # 运行列表
├── SubagentTimeline.tsx   # 执行步骤 Timeline
├── StatusBadge.tsx        # 状态标签
├── TerminateButton.tsx    # 终止按钮
└── SubagentDetail.tsx     # 子代理详情
```

### 验收标准

- [ ] 运行列表展示完整信息
- [ ] Timeline 展示执行步骤
- [ ] 可终止单个子代理
- [ ] 一键终止所有子代理

---

## 📦 F16 工具管理面板

**UI 先行，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 工具注册表 | Ant Design Table |
| 工具详情 | 名称、描述、JSON Schema |
| 调用统计 | 调用次数、成功率、平均耗时 |
| 工具测试 | 手动输入参数测试调用 |

### 组件拆分

```
tools/
├── ToolsPanel.tsx         # 主面板
├── ToolsTable.tsx         # 工具列表
├── ToolDetail.tsx         # 工具详情
├── ToolStats.tsx          # 调用统计
└── ToolTester.tsx         # 工具测试
```

### 验收标准

- [ ] 工具列表展示完整信息
- [ ] 调用统计图表展示
- [ ] 可手动测试工具调用

---

## 📦 F17 3D 桌面宠物窗口

**完全独立，纯前端，不依赖任何后端**

### 包含内容

| 功能 | 说明 |
|------|------|
| PMX 模型加载 | Three.js MMDLoader |
| 动作播放 | .vmd 动作文件 |
| 物理模拟 | ammojs 刚体模拟（头发/衣物） |
| 表情系统 | PMX morph 变形器 |
| 鼠标追踪 | 头部骨骼旋转追踪鼠标 |
| 点击交互 | 点击弹出属性面板 |
| 拖拽移动 | -webkit-app-region: drag |
| 性能优化 | 不可见时 5fps / 可见时 60fps |
| 资源释放 | 窗口关闭时 dispose |

### 组件拆分

```
pet-window/
├── PetWindow.tsx          # 宠物窗口主组件
├── PetScene.tsx           # Three.js 场景
├── PetModel.tsx           # PMX 模型加载
├── PetAnimation.tsx       # 动画控制
├── PetPhysics.tsx         # 物理模拟
├── PetExpression.tsx      # 表情控制
├── PetBubble.tsx          # 气泡对话
├── PetAttributePopup.tsx  # 属性弹窗
└── MouseTracker.tsx       # 鼠标追踪
```

### Electron 窗口配置

```typescript
const petWindowConfig = {
  width: 400,
  height: 500,
  transparent: true,
  frame: false,
  alwaysOnTop: true,
  resizable: false,
  skipTaskbar: true,
  webPreferences: {
    contextIsolation: true,
    nodeIntegration: false,
    preload: join(__dirname, '../preload/index.js'),
  },
};
```

### 验收标准

- [ ] PMX 模型正常加载显示
- [ ] 待机动作循环播放
- [ ] 头部追踪鼠标
- [ ] 点击弹出属性面板
- [ ] 窗口可拖拽移动
- [ ] 不可见时降帧
- [ ] 关闭时资源释放

---

## 📦 F18 宠物主窗口面板

**主窗口内的宠物控制中心，不做 3D，用截图预览**

> 主窗口宠物面板 **不做 3D 渲染**，用截图预览代替（从 3D 独立窗口截一帧展示）。
> 类似 QQ 宠物：主窗口看预览图 + 操作控制，真正的 3D 在独立宠物窗口(F17)运行。
> 省资源，主窗口不消耗 GPU。

### 包含内容

| Tab | 内容 |
|-----|------|
| 控制面板 Tab | 3D 窗口截图预览 + 开关 + 模型信息 + 实时状态 |
| 属性&互动 Tab | 六维属性 Progress + 喂食/清洁/聊天操作 + 互动记录 |
| 设置 Tab | 模型路径/窗口配置/衰减速度/气泡频率（从设置面板搬来） |

### 截图预览机制

```
宠物窗口 (独立 BrowserWindow)
  │
  ├─ 每 N 秒截一帧 (desktopCapturer / canvas.captureStream)
  │
  └─ 通过 IPC 发送给主窗口
       │
       主窗口宠物面板
         ├─ 展示最新截图（静态图，不消耗 GPU）
         └─ 宠物窗口关闭时显示默认占位图
```

### 组件拆分

```
pet/
├── PetPanel.tsx           # 主面板（Tabs 容器）
├── PetControlTab.tsx      # 控制面板 Tab（截图预览 + 开关 + 模型信息 + 实时状态）
├── PetScreenshotPreview.tsx # 截图预览组件（接收 IPC 截图更新）
├── PetStatusTab.tsx       # 属性&互动 Tab
├── PetSettingsTab.tsx     # 设置 Tab（从设置模块搬来）
├── PetInteraction.tsx     # 互动操作（喂食/清洁/聊天）
├── PetHistory.tsx         # 互动记录
└── AttributeBar.tsx       # 单个属性条
```

### 六维属性

```typescript
interface PetAttributes {
  hunger: number;    // 🍖 饥饿 (0-100)
  clean: number;     // 🧹 清洁 (0-100)
  mood: number;      // 😊 心情 (0-100)
  health: number;    // ❤️ 健康 (0-100)
  intimacy: number;  // 💕 亲密 (0-100)
  level: number;     // ⭐ 等级
}
```

### 验收标准

- [ ] 控制面板 Tab：截图预览正常显示（非 3D 渲染）
- [ ] 控制面板 Tab：开关可切换宠物状态
- [ ] 控制面板 Tab：模型信息展示
- [ ] 属性&互动 Tab：六维属性实时展示
- [ ] 属性&互动 Tab：喂食/清洁/聊天按钮可操作
- [ ] 属性&互动 Tab：互动记录列表
- [ ] 设置 Tab：模型路径/窗口/衰减/气泡频率可编辑
- [ ] 设置 Tab：打开宠物窗口按钮

---

## 📦 F19 性能监控面板

**UI 先行，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| CPU 使用率 | 实时图表 |
| 内存使用率 | 实时图表 |
| 磁盘使用率 | 实时图表 |
| 告警阈值 | CPU>80% / 内存>85% / 磁盘>90% |
| 趋势预测 | 基于历史数据线性回归 |

### 组件拆分

```
performance/
├── PerformancePanel.tsx   # 主面板
├── CpuChart.tsx           # CPU 图表
├── MemoryChart.tsx        # 内存图表
├── DiskChart.tsx          # 磁盘图表
├── AlertIndicator.tsx     # 告警指示器
└── TrendPrediction.tsx    # 趋势预测
```

### 图表技术选型

推荐 **echarts** 或 **recharts**，支持实时更新。

### 验收标准

- [ ] 三类图表实时更新
- [ ] 超过阈值红色告警
- [ ] 历史趋势可查看

---

## 📦 F20 通知中心

**UI 先行，数据用 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 通知弹窗 | Ant Design Notification 右上角 |
| 通知历史 | 按时间排列的列表 |
| 类型筛选 | 按来源类型筛选 |
| 标记已读 | 单条 / 全部标记已读 |
| 清除 | 清除已读通知 |
| 去重 | event_id 去重（LRU 缓存） |

### 组件拆分

```
notification/
├── NotificationPanel.tsx  # 主面板（通知历史）
├── NotificationItem.tsx   # 单条通知
├── NotificationFilter.tsx # 类型筛选
├── NotificationBadge.tsx  # 未读数角标
└── notification-toast.ts  # 弹窗工具函数
```

### 通知来源类型

```typescript
type NotificationType =
  | 'schedule_reminder'    // 📅 日程提醒
  | 'workflow_complete'    // ⚙️ 工作流完成
  | 'workflow_failed'      // ⚙️ 工作流失败
  | 'subagent_complete'    // 🤖 子代理完成
  | 'subagent_failed'      // 🤖 子代理失败
  | 'skill_suggestion'     // 💡 技能建议
  | 'system_alert'         // 📊 系统告警
  | 'config_update';       // ⚙️ 配置变更
```

### 验收标准

- [ ] 通知弹窗正常显示
- [ ] 通知历史列表
- [ ] 按类型筛选
- [ ] 未读数角标
- [ ] 全部标记已读

---

## 📦 F21 设置系统

**UI 先行，配置项用 mock**

### 包含内容

| 分区 | 配置项 |
|------|--------|
| Ollama 配置 | 服务地址、模型选择（对话/嵌入/视觉）、测试连接 |
| AI 设置 | Temperature、Max Tokens、Top-P、频率惩罚、AI 头像、系统提示词 |
| 应用设置 | 语言、开机自启、启动最小化、关闭行为 |
| 宠物设置 | 模型路径、窗口配置、衰减速度、气泡频率 |
| 快捷键设置 | 全局快捷键映射、冲突检测 |
| 隐私安全 | 数据加密、日志级别、匿名统计 |
| 关于更新 | 版本信息、检查更新、更新日志 |

### 组件拆分

```
settings/
├── SettingsPanel.tsx      # 主面板（Tabs 分区）
├── OllamaSettings.tsx     # Ollama 配置
├── AiSettings.tsx         # AI 设置
├── AppSettings.tsx        # 应用设置
├── PetSettings.tsx        # 宠物设置
├── HotkeySettings.tsx     # 快捷键设置
├── PrivacySettings.tsx    # 隐私安全
├── AboutUpdate.tsx        # 关于更新
└── ModelSelector.tsx      # 模型选择器
```

### 配置类型定义

```typescript
interface Settings {
  ollama: {
    host: string;
    chatModel: string;
    embeddingModel: string;
    visionModel: string;
  };
  ai: {
    temperature: number;
    maxTokens: number;
    topP: number;
    frequencyPenalty: number;
    aiAvatar: string;
    systemPrompt: string;
  };
  app: {
    language: string;
    autoStart: boolean;
    startMinimized: boolean;
    closeAction: 'exit' | 'minimize';
  };
  pet: {
    modelPath: string;
    windowOpacity: number;
    decaySpeed: 'slow' | 'normal' | 'fast';
    bubbleInterval: number;
  };
  hotkeys: Record<string, string>;
  privacy: {
    encryptData: boolean;
    logLevel: 'debug' | 'info' | 'warn' | 'error';
    anonymousStats: boolean;
  };
}
```

### 验收标准

- [ ] Tabs 分区切换
- [ ] 表单校验完整
- [ ] 保存后提示成功
- [ ] 需重启项提示重启
- [ ] 快捷键冲突检测

---

## 📦 F22 文件预览

**纯前端，不依赖后端**

### 包含内容

| 格式 | 实现 |
|------|------|
| 文本 (.txt) | react-codemirror 只读模式 |
| 代码 (.js/.py 等) | react-codemirror 语法高亮 |
| 图片 (.jpg/.png) | Ant Design Image 组件 |
| PDF | pdf.js 渲染 |

### 组件拆分

```
file-preview/
├── FilePreviewModal.tsx   # 预览弹窗
├── TextPreview.tsx        # 文本预览
├── CodePreview.tsx        # 代码预览
├── ImagePreview.tsx       # 图片预览
└── PdfPreview.tsx         # PDF 预览
```

### 验收标准

- [ ] 弹窗打开预览
- [ ] 文本/代码语法高亮
- [ ] 图片可缩放
- [ ] PDF 可翻页

---

## 📦 F23 OCR 截图识别

**纯前端 Tesseract.js，完全不依赖后端**

### 包含内容

| 功能 | 说明 |
|------|------|
| 图片上传 | 拖拽/选择图片 |
| OCR 识别 | Tesseract.js Web Worker |
| 多语言 | 中文简体 + 英文 |
| 结果展示 | 识别文本 + 置信度 |
| 一键复制 | 复制识别结果 |
| 历史记录 | 本地存储识别历史 |

### 组件拆分

```
ocr/
├── OcrPanel.tsx           # 主面板
├── ImageUploader.tsx      # 图片上传
├── OcrResult.tsx          # 识别结果
├── OcrProgress.tsx        # 识别进度
└── OcrHistory.tsx         # 历史记录
```

### 验收标准

- [ ] 图片拖拽上传
- [ ] OCR 识别正常工作
- [ ] 中英文识别准确
- [ ] 结果可复制
- [ ] 识别历史可查看

---

## 📦 F24 截图选区

**依赖 Electron desktopCapturer**

### 包含内容

| 功能 | 说明 |
|------|------|
| 屏幕捕获 | Electron desktopCapturer |
| 选区绘制 | Canvas overlay 画矩形 |
| 选区调整 | 拖拽调整大小 |
| 截图保存 | 保存到本地 |
| 发送 OCR | 发送到 OCR 模块识别 |

### 组件拆分

```
screenshot/
├── ScreenshotOverlay.tsx  # 全屏 Canvas overlay
├── SelectionRect.tsx      # 选区矩形
├── ScreenshotToolbar.tsx  # 截图工具栏
└── screenshot-ipc.ts      # IPC 通信
```

### 验收标准

- [ ] 快捷键触发截图
- [ ] 可绘制选区
- [ ] 选区可调整
- [ ] 截图可保存
- [ ] 可发送到 OCR

---

## 📦 F25 系统托盘 & 全局快捷键

**Electron 原生功能**

### 包含内容

| 功能 | 说明 |
|------|------|
| 系统托盘 | Tray + Menu |
| 显示/隐藏主窗口 | 托盘菜单操作 |
| 退出应用 | 托盘菜单操作 |
| 全局快捷键 | globalShortcut 注册 |
| 快捷键通知 | 通过 IPC 通知渲染进程 |

### 验收标准

- [ ] 托盘图标显示
- [ ] 右键菜单可用
- [ ] 全局快捷键响应
- [ ] 快捷键触发对应功能

---

## 📦 F26 离线存储 & 网络状态

**纯前端，IndexedDB + 网络监听**

### 包含内容

| 功能 | 说明 |
|------|------|
| 网络状态监听 | navigator.onLine + online/offline 事件 |
| 离线消息暂存 | IndexedDB 存储待发消息 |
| 恢复自动发送 | 网络恢复后自动发送 |
| 存储上限 | 500 条 / 10MB，FIFO 淘汰 |
| 状态指示 | 顶部横幅 + 底部状态栏 |

### IndexedDB 结构

```typescript
interface OfflineMessage {
  id: string;              // UUID
  conversationId: string;
  content: string;
  createdAt: number;
  status: 'pending' | 'sending' | 'failed';
  retryCount: number;
}
```

### 验收标准

- [ ] 断网时消息暂存
- [ ] 恢复网络自动发送
- [ ] 状态栏实时显示
- [ ] 离线横幅提示

---

## 📦 F27 多窗口 IPC 通信

**Electron 主进程协调**

### 包含内容

| 功能 | 说明 |
|------|------|
| 主窗口 → 宠物窗口 | 发送指令（切换模型、触发动画） |
| 宠物窗口 → 主窗口 | 上报事件（点击、属性变化） |
| 类型安全 | TypeScript 定义 IPC 通道类型 |
| 超时处理 | invoke 5s 超时 |
| 窗口状态检测 | isDestroyed() 检查 |

### IPC 通道定义

```typescript
// 主窗口 → 宠物窗口
interface PetIPCCommands {
  'pet:switchModel': (modelPath: string) => void;
  'pet:triggerAnimation': (animationName: string) => void;
  'pet:updateState': (attributes: PetAttributes) => void;
}

// 宠物窗口 → 主窗口
interface PetIPCEvents {
  'pet:onClick': () => void;
  'pet:attributeChange': (attributes: PetAttributes) => void;
  'pet:bubbleTrigger': (text: string) => void;
}
```

### 验收标准

- [ ] 双向 IPC 通信正常
- [ ] 窗口关闭不报错
- [ ] 超时处理正确
- [ ] 类型安全编译通过

---

## 📦 F28 WebSocket 通信层

**依赖后端 WebSocket 服务，但可独立开发客户端**

### 包含内容

| 功能 | 说明 |
|------|------|
| 连接管理 | 建立/断开/重连 |
| 心跳检测 | 30s ping/pong |
| 指数退避重连 | 初始 1s，最大 30s |
| 消息解析 | JSON 格式解析 |
| 事件分发 | 按 type 分发到各模块 |
| 断线重连去重 | event_id LRU 缓存 |

### 消息格式

```typescript
interface WSMessage {
  type: string;
  payload: any;
  timestamp: number;
  event_id: string;
}
```

### 验收标准

- [ ] 连接建立正常
- [ ] 心跳检测正常
- [ ] 断线自动重连
- [ ] 消息正确分发
- [ ] 重连后去重

---

## 📦 F29 AI 护栏 & 反馈系统

**UI 先行，逻辑 mock**

### 包含内容

| 功能 | 说明 |
|------|------|
| 反馈按钮 | 👍👎 每条 AI 回答 |
| 反馈原因标签 | 不准确/不相关/有害/其他 |
| 自由文本输入 | 补充说明 |
| 快速回答标识 | ⚡ 缓存回答标记 |
| 推理深度切换 | Segmented 三档 |

### 组件拆分

```
feedback/
├── FeedbackButtons.tsx    # 👍👎 按钮
├── FeedbackModal.tsx      # 反馈弹窗
├── ReasonTags.tsx         # 原因标签
└── QuickAnswerBadge.tsx   # ⚡ 快速回答标识
```

### 验收标准

- [ ] 👍👎 按钮响应
- [ ] 反馈弹窗表单
- [ ] 原因标签可选
- [ ] 提交反馈成功

---

## 🗓️ 推荐开发顺序

```
第一批（基础框架，3天）
  F01 脚手架 → F02 布局 → F03 主题 → F04 状态管理

第二批（核心交互，4天）
  F05 命令面板 → F06 聊天面板 → F08 剪贴板 → F09 代码片段

第三批（功能模块，6天）
  F07 日程 → F10 知识库 → F11 记忆 → F12 翻译 → F13 技能

第四批（复杂模块，5天）
  F14 工作流 → F15 子代理 → F16 工具管理

第五批（独立模块，5天）
  F17 3D 宠物窗口 → F18 宠物面板 → F19 性能监控 → F20 通知中心

第六批（系统功能，4天）
  F21 设置 → F22 文件预览 → F23 OCR → F24 截图

第七批（基础设施，3天）
  F25 托盘快捷键 → F26 离线存储 → F27 多窗口 IPC → F28 WebSocket → F29 反馈
```

---

## 📌 各块依赖关系图

```
F01 脚手架
  └─→ F02 布局 ─→ F03 主题
       └─→ F04 状态管理
            ├─→ F05 命令面板
            ├─→ F06 聊天 ─→ F29 反馈
            ├─→ F07 日程
            ├─→ F08 剪贴板
            ├─→ F09 代码片段
            ├─→ F10 知识库
            ├─→ F11 记忆
            ├─→ F12 翻译
            ├─→ F13 技能
            ├─→ F14 工作流
            ├─→ F15 子代理
            ├─→ F16 工具管理
            ├─→ F18 宠物面板 ←─ F17 3D 宠物 (独立)
            ├─→ F19 性能监控
            ├─→ F20 通知中心
            ├─→ F21 设置
            ├─→ F22 文件预览
            ├─→ F23 OCR ←─ F24 截图
            └─→ F26 离线存储

F25 托盘快捷键 (独立，依赖 Electron)
F27 多窗口 IPC (独立，依赖 Electron + F17)
F28 WebSocket (独立，可 mock)
```

---

> **说明**：标注 ✅ (mock) 的模块，开发时用 mock 数据替代后端 API，等环境就绪后接通即可。
> 标注 ❌ 的模块完全不依赖后端，可独立开发。
