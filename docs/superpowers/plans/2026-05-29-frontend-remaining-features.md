# Beautiful-Elf 前端剩余功能开发计划

> **For agentic workers:** 按任务逐个实现，每完成一个功能后运行 review 脚本检查代码，修复问题后提交到 dev 分支。

**目标:** 完成前端所有未实现功能模块

**架构:** Electron + React 19 + Ant Design v6 + Zustand + TypeScript

**技术栈:** React Flow (DAG编辑器)、IndexedDB (离线存储)、Three.js (3D宠物)、Electron IPC (多窗口)

---

## 依赖安装

### Task 0: 安装缺失依赖

**Files:**
- Modify: `web/package.json`

- [ ] **Step 1: 安装 React Flow**

```bash
cd web && npm install reactflow
```

- [ ] **Step 2: 安装 Three.js 及相关**

```bash
cd web && npm install three @types/three
```

- [ ] **Step 3: 安装 idb (IndexedDB 封装)**

```bash
cd web && npm install idb
```

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "deps: add reactflow, three.js, idb for remaining features"
```

---

## 并行组 A（无依赖，可同时开发）

### Task 1: F26 离线存储 IndexedDB

**Files:**
- Create: `web/src/renderer/modules/offline/services/offline-db.ts`
- Modify: `web/src/renderer/modules/offline/services/offline-storage.ts`
- Modify: `web/src/renderer/modules/offline/hooks/use-offline-queue.ts`
- Modify: `web/src/renderer/modules/offline/components/offline-stats.tsx`
- Modify: `web/src/renderer/modules/offline/offline-panel.tsx`

**核心功能:**
- IndexedDB 封装 (idb 库)
- OfflineMessage 存储/读取/删除
- FIFO 淘汰策略 (500条/10MB)
- 恢复网络后自动发送队列
- 底部状态栏网络状态显示
- 离线横幅提示

**验收标准:**
- [ ] IndexedDB 正常创建和读写
- [ ] 离线消息暂存和恢复发送
- [ ] 网络状态实时显示

---

### Task 2: F20 通知中心完善

**Files:**
- Modify: `web/src/renderer/modules/notification/notification-panel.tsx`
- Modify: `web/src/renderer/modules/notification/components/notification-panel.tsx`
- Modify: `web/src/renderer/modules/notification/components/notification-item.tsx`
- Create: `web/src/renderer/modules/notification/services/notification-toast.ts`
- Modify: `web/src/renderer/modules/notification/hooks/use-notification.ts`
- Modify: `web/src/renderer/modules/notification/types/notification.ts`

**核心功能:**
- event_id LRU 去重缓存 (100条)
- Electron 桌面原生通知 (Notification API)
- 通知弹窗点击跳转面板
- 按类型筛选/标记已读/清除
- WebSocket 通知事件接收

**验收标准:**
- [ ] 桌面通知正常弹出
- [ ] event_id 去重有效
- [ ] 通知历史可筛选

---

### Task 3: F21 Prompt 版本管理

**Files:**
- Create: `web/src/renderer/modules/settings/components/prompt-manager.tsx`
- Create: `web/src/renderer/modules/settings/components/prompt-version-history.tsx`
- Create: `web/src/renderer/modules/settings/components/prompt-diff.tsx`
- Modify: `web/src/renderer/modules/settings/settings-panel.tsx`
- Modify: `web/src/renderer/modules/settings/types/settings.ts`
- Modify: `web/src/renderer/modules/settings/services/settings-api.ts`

**核心功能:**
- Prompt 列表 (名称/版本/激活状态)
- 版本历史查看
- 版本 diff 对比
- A/B 测试配置

**验收标准:**
- [ ] Prompt 列表展示
- [ ] 版本历史可查看
- [ ] diff 对比清晰

---

### Task 4: F04 轮询管理 & 操作撤销

**Files:**
- Create: `web/src/renderer/services/polling-registry.ts`
- Create: `web/src/renderer/utils/undo-toast.ts`
- Modify: `web/src/renderer/stores/use-app-store.ts`
- Modify: `web/src/renderer/modules/schedule/hooks/use-schedule.ts`
- Modify: `web/src/renderer/modules/workflow/hooks/use-workflow.ts`

**核心功能:**
- PollingRegistry 统一管理轮询任务
- register/unregister/pause/resume
- UndoToast 30秒撤销操作
- 关键删除操作后弹出撤销提示

**验收标准:**
- [ ] 轮询任务可注册/暂停/恢复
- [ ] 删除操作后可撤销
- [ ] 30秒后自动消失

---

## 并行组 B（依赖安装完成后）

### Task 5: F14 工作流 DAG 编辑器

**Files:**
- Modify: `web/src/renderer/modules/workflow/components/workflow-editor.tsx`
- Modify: `web/src/renderer/modules/workflow/components/workflow-list.tsx`
- Modify: `web/src/renderer/modules/workflow/components/workflow-monitor.tsx`
- Modify: `web/src/renderer/modules/workflow/components/workflow-templates.tsx`
- Modify: `web/src/renderer/modules/workflow/components/workflow-panel.tsx`
- Modify: `web/src/renderer/modules/workflow/hooks/use-workflow.ts`
- Modify: `web/src/renderer/modules/workflow/services/workflow-api.ts`
- Modify: `web/src/renderer/modules/workflow/types/workflow.ts`
- Modify: `web/src/renderer/modules/workflow/workflow-panel.tsx`

**核心功能:**
- React Flow DAG 可视化编辑器
- 节点拖拽添加/移动
- 节点间连线定义依赖
- 节点配置面板
- 模板系统 (预置工作流)
- 运行监控 (实时节点状态)
- 运行历史

**验收标准:**
- [ ] 可拖拽添加节点
- [ ] 节点间可连线
- [ ] 选中节点可配置参数
- [ ] 预置模板可一键创建
- [ ] 运行状态实时展示

---

### Task 6: F17 3D 宠物窗口 + F27 多窗口 IPC

**Files:**
- Create: `web/src/main/pet-window.ts`
- Modify: `web/src/main/window-manager.ts`
- Modify: `web/src/main/ipc-handlers.ts`
- Modify: `web/src/main/index.ts`
- Create: `web/src/renderer/modules/pet/components/pet-screenshot-preview.tsx`
- Create: `web/src/renderer/modules/pet/components/pet-settings-tab.tsx`
- Modify: `web/src/renderer/modules/pet/pet-panel.tsx`
- Modify: `web/src/renderer/modules/pet/components/pet-control-tab.tsx`
- Modify: `web/src/renderer/modules/pet/services/pet-api.ts`
- Modify: `web/src/renderer/modules/pet/hooks/use-pet.ts`
- Modify: `web/src/renderer/modules/pet/types/pet.ts`

**核心功能:**
- 宠物独立 BrowserWindow (透明/无边框/置顶)
- Three.js PMX 模型加载 (MMDLoader)
- 物理模拟 (ammojs 刚体)
- 动作播放 (.vmd)
- 表情系统 (morph)
- 鼠标追踪 (头部骨骼)
- 性能自适应 (不可见5fps/可见60fps)
- 离线差值结算
- IPC 通道定义 (类型安全)
- 超时处理 (5s)
- 截图预览机制 (IPC 传输)
- 气泡对话 (AI生成)

**验收标准:**
- [ ] 宠物窗口独立显示
- [ ] PMX 模型加载正常
- [ ] 头部追踪鼠标
- [ ] IPC 双向通信正常
- [ ] 截图预览在主窗口显示
- [ ] 离线结算正确

---

### Task 7: F28 WebSocket 完善

**Files:**
- Modify: `web/src/renderer/services/websocket/websocket-client.ts`
- Modify: `web/src/renderer/services/websocket/websocket-provider.tsx`
- Modify: `web/src/renderer/services/websocket/message-queue.ts`
- Modify: `web/src/renderer/services/websocket/use-websocket.ts`
- Modify: `web/src/renderer/services/websocket/types.ts`

**核心功能:**
- 心跳检测 (30s ping/pong)
- 指数退避重连 (初始1s, 最大30s)
- 断线重连去重 (event_id LRU)
- 消息队列 (断线时缓存)
- 各模块事件分发

**验收标准:**
- [ ] 心跳检测正常
- [ ] 断线自动重连
- [ ] 消息去重有效
- [ ] 断线消息不丢失

---

## 收尾

### Task 8: API 字段转换层 & 错误上报

**Files:**
- Modify: `web/src/renderer/services/api-client.ts`
- Create: `web/src/renderer/services/error-reporter.ts`
- Modify: `web/src/renderer/services/api-error.ts`

**核心功能:**
- Axios 拦截器 (camelCase↔snake_case)
- 全局错误上报到后端 (/api/v1/errors)
- 错误截断 (stack 2000字, componentStack 1000字)

**验收标准:**
- [ ] API 字段自动转换
- [ ] 错误正常上报
- [ ] 上报失败静默处理

---

### Task 9: 测试补全 & 最终审查

**Files:**
- 各模块 `__tests__/` 目录

**核心功能:**
- 补全缺失模块的单元测试
- 运行全量测试
- 最终代码审查
- 性能检查

**验收标准:**
- [ ] 所有测试通过
- [ ] TypeScript 编译无报错
- [ ] ESLint 无警告
