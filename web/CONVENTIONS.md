# Beautiful-Elf 前端开发规范

> 所有子代理必须严格遵守此规范，确保代码风格一致。

## 技术栈（固定版本）
- Electron 41 + electron-vite 3
- React 19 + TypeScript 6
- Ant Design v6（组件库）
- Zustand 5（客户端状态）
- TanStack Query 5（服务端状态缓存）
- React Hook Form 7 + Zod 4（表单校验）
- Axios 1.x（HTTP 请求）
- react-window 1.x（虚拟滚动）
- react-codemirror（代码编辑器）
- Three.js r181 + @react-three/fiber 9 + drei 9（3D）

## 目录结构
```
web/src/
├── main/                    # Electron 主进程
│   ├── index.ts             # 入口
│   ├── window-manager.ts   # 窗口管理
│   ├── tray.ts             # 系统托盘
│   └── ipc-handlers.ts     # IPC 处理
├── preload/
│   └── index.ts            # 预加载脚本
├── renderer/
│   ├── App.tsx             # 根组件
│   ├── main.tsx            # 渲染进程入口
│   ├── assets/             # 静态资源
│   ├── components/         # 公共组件
│   │   ├── layout/         # 布局组件
│   │   ├── error-boundary/ # 错误边界
│   │   └── loading/        # 加载态
│   ├── modules/            # 功能模块（每个模块独立目录）
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
│   ├── stores/             # Zustand stores
│   ├── hooks/              # 自定义 hooks
│   ├── services/           # API 调用层（Axios 封装）
│   ├── utils/              # 工具函数
│   ├── types/              # TypeScript 类型定义
│   └── styles/             # 全局样式
└── shared/                 # 主进程 & 渲染进程共享
    └── constants.ts
```

## 命名规约（P3C）
| 类型 | 规则 | 示例 |
|------|------|------|
| 文件名 | kebab-case | `schedule-panel.tsx`, `use-auto-scroll.ts` |
| 组件名 | PascalCase | `SchedulePanel`, `MessageBubble` |
| 函数/变量 | camelCase | `getScheduleById`, `isLoading` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `API_BASE_URL` |
| 类型/接口 | PascalCase | `ScheduleItem`, `ChatMessage` |
| Hook | use 前缀 | `useAutoScroll`, `useDebounce` |
| 枚举 | PascalCase + 值 UPPER_SNAKE | `enum Status { PENDING, RUNNING }` |
| CSS Module | camelCase | `styles.chatContainer` |
| 路由路径 | kebab-case | `/schedule-reminders` |

## API 字段命名转换
- 后端统一 snake_case，前端统一 camelCase
- 在 Axios 拦截器层自动转换
- **类型定义必须与数据库表结构一一对应**（camelCase 版本）
- 全局类型定义在 `types/index.ts`，模块类型定义在 `modules/*/types/*.ts`
- 所有类型字段必须使用 camelCase，禁止在前端代码中出现 snake_case 字段引用

## 数据库字段对照规则
| 数据库 (snake_case) | 前端 (camelCase) | 说明 |
|---------------------|------------------|------|
| `created_at` | `createdAt` | 所有表通用 |
| `updated_at` | `updatedAt` | 所有表通用 |
| `is_all_day` | `allDay` | schedules 表，类型为 number (0/1) |
| `repeat_type` | `repeatType` | schedules 表，类型为 number (0-4) |
| `reminder_minutes` | `reminderMinutes` | schedules 表 |
| `content_type` | `contentType` | clipboard_items 表 |
| `source_app` | `sourceApp` | clipboard_items 表 |
| `use_count` | `useCount` | snippets/commands 表 |
| `file_type` | `fileType` | knowledge_documents 表 |
| `chunk_count` | `chunkCount` | knowledge_documents 表 |
| `conversation_id` | `conversationId` | messages/memory_entries 表 |
| `tool_calls` | `toolCalls` | messages 表 |
| `tool_call_id` | `toolCallId` | messages 表 |
| `token_count` | `tokenCount` | messages 表 |
| `dag_json` | `dagJson` | workflows 表 |
| `json_schema` | `jsonSchema` | tools 表 |
| `trigger_words` | `triggerWords` | skills 表 |
| `display_name` | `displayName` | 多表通用 |
| `shortcut_key` | `shortcutKey` | commands 表 |
| `command_type` | `commandType` | commands 表 |
| `qdrant_point_id` | `qdrantPointId` | 向量关联字段 |
| `hit_count` | `hitCount` | intent_usage 表 |
| `avg_confidence` | `avgConfidence` | intent_usage 表 |
| `last_hit_at` | `lastHitAt` | intent_usage 表 |
| `call_count` | `callCount` | stats 表 |
| `success_count` | `successCount` | stats 表 |
| `fail_count` | `failCount` | stats 表 |
| `avg_duration_ms` | `avgDurationMs` | stats 表 |
| `last_called_at` | `lastCalledAt` | stats 表 |
| `last_used_at` | `lastUsedAt` | command_usage 表 |
| `last_active_at` | `lastActiveAt` | pet_attributes 表 |
| `interaction_type` | `interactionType` | pet_interactions 表 |
| `effect_json` | `effectJson` | pet_interactions 表 |
| `cpu_percent` | `cpuPercent` | performance_metrics 表 |
| `memory_percent` | `memoryPercent` | performance_metrics 表 |
| `memory_used_mb` | `memoryUsedMb` | performance_metrics 表 |
| `disk_percent` | `diskPercent` | performance_metrics 表 |
| `disk_used_gb` | `diskUsedGb` | performance_metrics 表 |
| `gpu_percent` | `gpuPercent` | performance_metrics 表 |
| `backup_type` | `backupType` | backup_records 表 |
| `file_path` | `filePath` | backup_records 表 |
| `file_size` | `fileSize` | 多表通用 |
| `error_message` | `errorMessage` | 多表通用 |
| `params_summary` | `paramsSummary` | action_logs 表 |
| `session_id` | `sessionId` | action_logs 表 |
| `system_prompt` | `systemPrompt` | soul_configs 表 |
| `speaking_style` | `speakingStyle` | soul_configs 表 |
| `avatar_url` | `avatarUrl` | soul_configs 表 |
| `is_active` | `isActive` | 多表通用 |
| `restart_required` | `restartRequired` | settings 表 |
| `event_id` | `eventId` | 通知去重 |
| `action_url` | `actionUrl` | 通知跳转 |
| `model_name` | `modelName` | conversations 表 |
| `message_count` | `messageCount` | conversations 表 |
| `last_message_at` | `lastMessageAt` | conversations 表 |
| `started_at` | `startedAt` | 多表通用 |
| `finished_at` | `finishedAt` | workflow_runs 表 |
| `duration_ms` | `durationMs` | 多表通用 |
| `step_name` | `stepName` | workflow_step_runs 表 |
| `step_type` | `stepType` | workflow_step_runs 表 |
| `input_json` | `inputJson` | 多表通用 |
| `output_json` | `outputJson` | 多表通用 |
| `trigger_type` | `triggerType` | workflows 表 |
| `cron_expr` | `cronExpr` | workflows 表 |
| `event_trigger` | `eventTrigger` | workflows 表 |
| `workflow_id` | `workflowId` | workflow_runs 表 |
| `run_id` | `runId` | workflow_step_runs 表 |
| `skill_id` | `skillId` | skill_stats 表 |
| `tool_id` | `toolId` | tool_stats 表 |
| `intent_id` | `intentId` | intent_usage 表 |
| `command_id` | `commandId` | command_usage 表 |
| `document_id` | `documentId` | knowledge_chunks 表 |
| `chunk_index` | `chunkIndex` | knowledge_chunks 表 |
| `content_preview` | `contentPreview` | knowledge_chunks 表 |
| `target_module` | `targetModule` | intents 表 |
| `trigger_texts` | `triggerTexts` | intents 表 |
| `reason_tags` | `reasonTags` | ai_feedback 表 |
| `reason_text` | `reasonText` | ai_feedback 表 |
| `trace_id` | `traceId` | 多表通用 |
| `feedback_type` | `feedbackType` | ai_feedback 表 |

## 设计方向
- **风格**：现代简约，温暖亲切（桌面宠物助手调性）
- **色彩**：主色调温暖橙黄系，辅助色用柔和蓝绿，避免纯黑纯白
- **字体**：中文用系统字体（PingFang SC / Microsoft YaHei），英文用 Inter
- **圆角**：统一 8px 中等圆角，卡片 12px
- **间距**：基础单位 8px，用 8/12/16/24/32 的倍数
- **暗色模式**：必须支持，用 Ant Design ConfigProvider 暗色算法
- **避免**：glassmorphism、渐变文字、纯黑纯白、卡片套卡片

## 通用组件提取原则
- 所有模块共用的 UI 元素提取到 `components/` 目录
- 包括：ErrorBoundary、Loading/Skeleton、PageHeader、EmptyState、ConfirmDialog
- 模块内共用的放模块目录内的 `components/` 子目录

## 状态管理规范
- 客户端状态（UI 状态、本地缓存）→ Zustand store
- 服务端状态（API 数据缓存）→ TanStack Query
- 表单状态 → React Hook Form
- 不要混用，职责分明

## 测试规范
- 测试框架：Vitest + @testing-library/react
- 测试文件与源文件同目录，命名 `*.test.tsx`
- 关键组件必须有单元测试

## 代码提交规范
- conventional-commits：feat/fix/docs/refactor/test/chore
- 提交信息格式：`type(scope): description`
