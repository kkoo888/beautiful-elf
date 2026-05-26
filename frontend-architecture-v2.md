# Beautiful-Elf 前端架构图 v2

## 🖥️ Electron 主窗口 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Electron 主窗口                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────────────────────────────┐    │
│  │  侧边栏导航   │  │              主内容区                      │    │
│  │              │  │                                          │    │
│  │  💬 对话     │◄─┐│  ┌────────────────────────────────────┐  │    │
│  │  📅 日程     │  ││  │  💬 聊天面板 (默认首页)              │  │    │
│  │  📋 剪贴板   │  ││  │                                    │  │    │
│  │  💻 代码片段  │  ││  │  用户输入                           │  │    │
│  │  📚 知识库   │  ││  │  ↓                                 │  │    │
│  │  🧠 记忆     │  ││  │  意图识别 (Qdrant+Qwen3-Embedding)  │  │    │
│  │  🌐 翻译 ✨  │  ││  │  ↓                                 │  │    │
│  │  🔧 技能     │  ││  │  命中→路由模块  未命中→通用对话       │  │    │
│  │  ⚙️ 工作流   │  ││  │  ↓                                 │  │    │
│  │  🤖 子代理   │  ││  │  流式回答 + 👍👎 + ⚡ + 推理深度切换  │  │    │
│  │  📊 性能监控  │  ││  └────────────────────────────────────┘  │    │
│  │  🔌 工具管理  │  ││                                          │    │
│  │  🔔 通知 ✨  │  │├─→ 📅 日程面板 (月/周/日+CRUD+提醒)       │    │
│  │  🐾 宠物 ✨  │  │├─→ 📋 剪贴板面板 (历史+搜索/固定/复制)    │    │
│  │  ⚙️ 设置    │  │├─→ 💻 代码片段面板 (CodeMirror+标签)      │    │
│  │              │  │├─→ 📚 知识库管理面板 (导入/删除/回收站)    │    │
│  │              │  │├─→ 🧠 记忆面板 (长期记忆+语义检索)        │    │
│  │              │  │├─→ 🌐 翻译面板 (语言选择+原文/译文对照)    │    │
│  │              │  │├─→ 🔧 技能面板 (安装/启用/炼化/链式)      │    │
│  │              │  │├─→ ⚙️ 工作流面板 (DAG+模板+监控)         │    │
│  │              │  │├─→ 🤖 子代理面板 (列表+Timeline+终止)     │    │
│  │              │  │├─→ 📊 性能监控面板 (CPU/内存/磁盘图表)    │    │
│  │              │  │├─→ 🔌 工具管理面板 (注册表+调用统计)      │    │
│  │              │  │├─→ 🔔 通知面板 (日程/工作流/子代理/告警)   │    │
│  │              │  │├─→ 🐾 宠物面板                           │    │
│  │              │  ││    ├─ 控制面板 Tab: 截图预览+开关+模型信息  │    │
│  │              │  ││    ├─ 属性&互动 Tab: 六维+喂食/清洁/聊天  │    │
│  │              │  ││    └─ 设置 Tab: 模型路径/窗口/衰减/气泡   │    │
│  │              │  │├─→ ⚙️ 设置面板                           │    │
│  │              │  ││    Ollama/AI/应用/快捷键/隐私/关于        │    │
│  │              │  ││    (宠物设置已搬走)                       │    │
│  └──────────────┘  └──────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  🔍 命令面板 (Modal, Ctrl+K 全局唤起) — 不占侧边栏           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  📸 截图选区 (Canvas overlay) — 快捷键触发                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  📄 文件预览弹窗 — 聊天中点击文件触发                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  📌 底部状态栏: 网络状态(在线/离线/同步中) + 撤销提示          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  🐾 宠物窗口 (独立 BrowserWindow)                                    │
│  透明 + 无边框 + 置顶 + 400×500                                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Three.js Canvas (PMX 模型 + 物理模拟 + 动作 + 表情)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌───────────────┐  ┌─────────────────────────────────────────┐   │
│  │  气泡对话      │  │  属性面板 (点击宠物弹出 Modal)            │   │
│  │  AI 生成自然语言│  │  🍖🧹😊❤️💕⭐                           │   │
│  └───────────────┘  └─────────────────────────────────────────┘   │
│  离线结算 | 性能自适应(不可见5fps/可见60fps)                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  📌 系统托盘 (Tray Menu)                                            │
│  显示/隐藏主窗口 / 退出                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 侧边栏导航

| 分组 | 模块 | 说明 |
|------|------|------|
| 📁 核心 | 💬 对话 | 默认首页 |
| | 📅 日程 | 月/周/日视图 |
| | 📋 剪贴板 | 历史/搜索/固定 |
| | 💻 代码片段 | CodeMirror 编辑器 |
| 📁 知识 & AI | 📚 知识库 | 文档导入/管理 |
| | 🧠 记忆 | 长期记忆 + 语义检索 |
| | 🌐 翻译 ✨新增 | 术语优先 + RAG 增强 |
| | 🔧 技能 | 安装/炼化/链式配置 |
| 📁 自动化 | ⚙️ 工作流 | DAG 编辑 + 运行监控 |
| | 🤖 子代理 | 运行列表 + Timeline |
| | 🔌 工具管理 | 注册表 + 调用统计 |
| 📁 系统 | 🐾 宠物 ✨新增 | 属性展示 + 控制 |
| | 📊 性能监控 | CPU/内存/磁盘图表 |
| | 🔔 通知 ✨新增 | 通知历史中心 |
| | ⚙️ 设置 | 全局配置 |

---

### 主内容区

#### 💬 聊天面板（默认首页）

```
用户输入
  ↓
意图识别 (Qdrant + Qwen3-Embedding)
  ↓
├─ 命中意图 → 路由到对应模块工具
└─ 未命中 → 通用对话 (RAG + LLM)
  ↓
流式回答展示
  + 👍👎 反馈
  + ⚡ 快速回答标识
  + 推理深度切换 (快速 / 深度 / 全面)
```

#### 各功能面板

| 面板 | 功能 |
|------|------|
| 📅 日程 | 月/周/日视图 + CRUD，定时任务 → 🔔 通知弹窗提醒 |
| 📋 剪贴板 | 历史列表 + 搜索/固定/复制 |
| 💻 代码片段 | CodeMirror 编辑器 + 标签管理 |
| 📚 知识库 | 文档导入/删除/回收站/导出 |
| 🧠 记忆 | 长期记忆列表 + 语义检索 |
| 🌐 翻译 | 语言选择 + 原文/译文对照，翻译(通用) / 小希翻译(术语+RAG)，历史/收藏 |
| 🔧 技能 | 安装/启用/禁用/炼化/链式配置 |
| ⚙️ 工作流 | DAG 编辑 + 模板 + 运行监控，完成/失败 → 🔔 通知弹窗 |
| 🤖 子代理 | 运行列表 + Timeline + 终止，完成/失败 → 🔔 通知弹窗 |
| 📊 性能监控 | CPU/内存/磁盘实时图表，告警 → 🔔 通知弹窗 |
| 🔌 工具管理 | 工具注册表 + 调用统计 |
| 🔔 通知 | 通知历史中心（见下方详细说明） |
| 🐾 宠物 | 仅属性展示和控制（见下方详细说明） |
| ⚙️ 设置 | Ollama / AI / 应用 / 快捷键 / 隐私安全 / 关于更新（宠物设置已搬走） |

---

### 🔔 通知面板（统一通知中心）

> 所有后台触发的通知统一汇聚于此，通过 Ant Design Notification 弹窗即时提醒，并写入通知历史列表。

| 来源 | 后端触发方式 | 通知内容示例 |
|------|-------------|-------------|
| 📅 日程提醒 | Celery Beat 扫描 | "会议在 30 分钟后" |
| ⚙️ 工作流完成 | LangGraph 回调 | "文档处理完成" |
| 🤖 子代理状态 | LangGraph 状态机 | "子代理 #3 已完成" |
| 💡 技能建议 | PatternDetector | "建议创建 xx 技能" |
| 📊 系统告警 | psutil 阈值检测 | "CPU 使用率 > 80%" |

**通知流：**

```
后台任务 (Celery / LangGraph / psutil)
  ↓
WebSocket 推送通知事件到前端
  ↓
通知中心统一处理
  ├─→ 去重检查 (event_id 去重，见下方说明)
  ├─→ Ant Design Notification 弹窗 (右上角, 即时提醒)
  │     点击弹窗 → 跳转通知面板
  └─→ 写入通知历史列表
        按类型筛选 / 标记已读 / 清除
```

**WebSocket 断线重连去重策略**:
- 每条 WebSocket 消息携带 `event_id` (UUID)
- 前端维护最近 100 条 `event_id` 的 LRU 缓存
- 收到消息时先检查 `event_id` 是否已处理过，已处理则跳过
- 断线重连时服务端不重推历史消息（客户端通过 REST API 拉取缺失数据）

---

### 🐾 宠物面板（截图预览 + 控制 + 设置）

> 主窗口宠物面板 **不做 3D 渲染**，用截图预览代替（从 3D 独立窗口截一帧展示）。
> 类似 QQ 宠物：主窗口看预览图 + 操作控制，真正的 3D 在独立宠物窗口运行。

| Tab | 内容 |
|-----|------|
| 控制面板 Tab | 3D 窗口截图预览 + 开关 + 模型信息 + 实时状态 |
| 属性&互动 Tab | 六维属性 Progress + 喂食/清洁/聊天操作 + 互动记录 |
| 设置 Tab | 模型路径 / 窗口配置 / 衰减速度 / 气泡频率（从设置面板搬来） |

**截图预览机制**：
- 宠物窗口每 N 秒截一帧，通过 IPC 发送给主窗口
- 主窗口展示最新截图作为预览（静态图，不消耗 GPU）
- 宠物窗口关闭时显示默认占位图

**注意**: 宠物设置已从设置面板搬到这里，设置面板不再包含宠物配置。

---

### 🔄 全局状态设计

#### 全局加载态

| 层级 | 场景 | 实现 |
|------|------|------|
| 面板级 | 面板切换懒加载 | `React.lazy` + `Suspense` → Ant Design **Skeleton** 骨架屏 |
| 数据级 | 首次加载 | TanStack Query → Skeleton / Spin |
| 数据级 | 刷新数据 | 保留旧数据 + 右上角小 Spin 提示 |
| 数据级 | 提交操作 | 按钮 `loading` 状态 + 禁用 |

#### 全局错误态

| 层级 | 范围 | 展示 | 操作 |
|------|------|------|------|
| **应用级** | 全局 `ErrorBoundary` | 全屏错误卡片："应用遇到了问题" | [重新加载] → `location.reload()` |
| **模块级** | 每个功能独立 `ErrorBoundary` | 模块内错误卡片："日程模块加载失败" | [重新加载此模块] |
| **网络级** | 底部状态栏实时显示 | 🟢 在线 / 🔴 离线 / 🟡 同步中 | 离线时消息暂存 IndexedDB，恢复后自动发送 |

**网络级补充：**
- 离线时顶部横幅提示："网络已断开，部分功能暂不可用"
- 聊天消息暂存 IndexedDB，恢复网络后自动发送
- 日程数据可从 Redis 缓存查看（只读）

---

### 覆盖层组件（不占侧边栏）

| 组件 | 触发方式 | 说明 |
|------|---------|------|
| 🔍 命令面板 | `Ctrl+K` 全局唤起 | Modal + AutoComplete，支持模块动态注册 |
| 📸 截图选区 | 快捷键触发 | Canvas overlay，Electron desktopCapturer |
| 📄 文件预览 | 聊天中点击文件 | Modal，支持文本/代码/图片/PDF |
| 📌 底部状态栏 | 常驻 | 网络状态 + 撤销提示 |

#### 🔍 命令面板排序规则

```
输入关键词 → 匹配命令列表 → 排序:
  1. 精确匹配 (命令名完全匹配) → 最前
  2. 前缀匹配 (命令名以关键词开头)
  3. 模糊匹配 (包含关键词)
  4. 同匹配度内按使用频率降序 (command_usage.use_count)
  5. 同频率按最近使用时间降序 (command_usage.last_used_at)
  最多显示 20 条结果
```

---

### 📄 离线 IndexedDB 存储结构

> 断网时聊天消息暂存到 IndexedDB，恢复后自动发送。

```typescript
// 数据库名: beautiful-elf-offline
// 版本: 1

interface OfflineMessage {
  id: string;              // UUID
  conversationId: string;  // 会话 ID
  content: string;         // 消息内容
  createdAt: number;       // 时间戳
  status: 'pending' | 'sending' | 'failed';
  retryCount: number;      // 重试次数
}

// 存储上限: 500 条消息 或 10MB (取先到者)
// 超出时 FIFO 淘汰最旧的消息
// 恢复网络后按 createdAt 顺序逐条发送
```

---

## 🐾 宠物窗口（独立 BrowserWindow）

> 透明 + 无边框 + 置顶 + 400×500

| 区域 | 内容 |
|------|------|
| **Three.js Canvas** | PMX 模型 + 物理模拟 (ammojs) + 动作 (.vmd) + 表情 (morph) + 鼠标追踪 |
| **气泡对话** | AI 生成自然语言，根据宠物状态触发 |
| **属性面板** | 点击宠物弹出 Modal：🍖 饥饿 / 🧹 清洁 / 😊 心情 / ❤️ 健康 / 💕 亲密 / ⭐ 等级 |

**性能优化：**
- 离线差值结算：关闭时记录时间戳，重开时根据离线时长计算属性衰减
- 性能自适应：窗口不可见 5fps / 可见 60fps
- 资源释放：`renderer.dispose()` + `scene.clear()` 节省内存

### IPC 通信错误处理

> 主窗口与宠物窗口通过 Electron IPC 通信，必须处理窗口关闭/进程崩溃的情况。

```typescript
// 主窗口 → 宠物窗口 (发送指令)
function sendToPetWindow(channel: string, data: any): void {
  const petWindow = BrowserWindow.getAllWindows().find(w => w.id === petWindowId);
  if (!petWindow || petWindow.isDestroyed()) {
    logger.warn("宠物窗口已关闭，丢弃 IPC 消息: {}", channel);
    return;
  }
  petWindow.webContents.send(channel, data);
}

// 宠物窗口 → 主窗口 (上报事件)
// 使用 ipcRenderer.invoke (Promise 化)，设置超时
const result = await ipcRenderer.invoke('pet:getAttributes');
// 超时处理: 5 秒无响应 → 提示用户宠物窗口可能卡死

// 主进程 IPC handler 错误兜底
ipcMain.handle('pet:getAttributes', async (event) => {
  try {
    return await getPetAttributes();
  } catch (error) {
    logger.error("宠物属性获取失败: {}", error.message);
    return { error: 'PET_WINDOW_ERROR', message: '宠物窗口通信异常' };
  }
});
```

**IPC 错误场景**:

| 场景 | 处理 |
|------|------|
| 宠物窗口已关闭 | 检查 `window.isDestroyed()`，丢弃消息并日志 |
| 宠物窗口进程崩溃 | 监听 `render-process-gone` 事件，自动重启窗口 |
| IPC 调用超时 | invoke 设置 5s 超时，超时返回降级数据 |
| 主窗口已关闭 | 宠物窗口检测 `ipcRenderer` 断开，独立运行 |

---

## 📌 系统托盘（Tray Menu）

- 显示 / 隐藏主窗口
- 退出应用

---

## 📐 前端命名规约

> 遵循 P3C 规范，TypeScript/React 统一约定。

| 类型 | 规则 | 示例 |
|------|------|------|
| 文件名 | kebab-case | `schedule-panel.tsx`, `use-auto-scroll.ts` |
| 组件名 | PascalCase | `SchedulePanel`, `MessageBubble` |
| 函数/变量 | camelCase | `getScheduleById`, `isLoading` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `API_BASE_URL` |
| 类型/接口 | PascalCase | `ScheduleItem`, `ChatMessage` |
| Hook | use 前缀 | `useAutoScroll`, `useDebounce` |
| 枚举 | PascalCase + 枚举值 UPPER_SNAKE | `enum Status { PENDING, RUNNING }` |
| CSS Module | camelCase | `styles.chatContainer` |
| 路由路径 | kebab-case | `/schedule-reminders` |

### API 字段命名转换

> 后端统一 snake_case，前端统一 camelCase，在 API 边界层自动转换。

```typescript
// Axios 请求拦截器: camelCase → snake_case
axios.interceptors.request.use((config) => {
  config.data = camelToSnake(config.data);
  return config;
});

// Axios 响应拦截器: snake_case → camelCase
axios.interceptors.response.use((response) => {
  response.data = snakeToCamel(response.data);
  return response;
});

// 工具函数
const camelToSnake = (obj: Record<string, any>): Record<string, any> =>
  Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [
      k.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`),
      v,
    ])
  );

const snakeToCamel = (obj: Record<string, any>): Record<string, any> =>
  Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [
      k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()),
      v,
    ])
  );
```

---

## 🛡️ 前端异常处理

```typescript
// 应用级 ErrorBoundary (全局兜底)
<App>
  <ErrorBoundary fallback={<GlobalErrorCard />}>
    {/* 所有内容 */}
  </ErrorBoundary>
</App>

// 模块级 ErrorBoundary (每个功能独立)
<ErrorBoundary 
  fallback={<ModuleErrorCard moduleName="日程" />}
  onError={(error, info) => logErrorToBackend(error, info)}
>
  <SchedulePanel />
</ErrorBoundary>

// TanStack Query 错误处理
useQuery({
  queryKey: ['schedules'],
  queryFn: fetchSchedules,
  retry: 2,                          // 失败重试 2 次
  retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),  // 指数退避
})

// 全局未捕获错误
window.addEventListener('unhandledrejection', (event) => {
  logErrorToBackend(event.reason)
  event.preventDefault()
})

// 错误上报函数
async function logErrorToBackend(error: any, info?: React.ErrorInfo) {
  try {
    await axios.post('/api/v1/errors', {
      message: error?.message || String(error),
      stack: error?.stack?.slice(0, 2000),  // 截断过长堆栈
      component_stack: info?.componentStack?.slice(0, 1000),
      url: window.location.href,
      user_agent: navigator.userAgent,
      timestamp: Date.now(),
    });
  } catch {
    // 上报失败时静默处理，不抛出新错误
    electronLog.error('错误上报失败:', error);
  }
}
```

---

## 📝 前端日志规约

| 规则 | 实现 |
|------|------|
| trace_id 生成 | 请求发起时生成 UUID，注入 Axios 请求头 `X-Trace-Id` |
| 错误上报 | `electron-log` 分级输出到本地文件 |
| 敏感数据脱敏 | 用户消息内容截断显示，API Key 不入日志 |
| 按模块分文件 | `chat.log`, `pet.log`, `schedule.log` |
| 日志轮转 | 单文件 10MB，最多 5 个归档 |
