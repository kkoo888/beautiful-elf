# 智能桌面助手 — 功能说明文档

> 基于项目实际代码更新，仅保留功能描述，不含代码。

---

## 项目概述

基于 Electron + React + TypeScript 的智能桌面助手，采用模块化架构，支持 23 个功能模块，通过 AI 调度器实现意图识别与工具路由。

**技术栈**：Electron 33 + React 18 + Vite 5 + TypeScript 5 + Zustand + SQLite (better-sqlite3) + Ollama

---

## 核心系统（src/main/core）

### 事件总线系统

- **GlobalEventBus**：全局事件总线，基于 Node.js EventEmitter，支持 on/off/emit/once/removeAllListeners
- **ModuleScopedEventBus**：模块限定范围事件总线，按 module.json 的 provides/consumes 声明控制事件收发权限，未声明的事件自动拦截并告警
- **错误隔离**：事件处理器异常不影响其他处理器，错误通过 `_error` 事件上报
- **内存管理**：handlerMap 三层映射结构支持精确取消，removeAllListeners 按事件名或全局清理

### 统一日志系统

- **AppLogger**：模块级日志器，支持 debug/info/warn/error 四级
- **多传输器**：ConsoleTransport（控制台输出）+ FileTransport（文件输出，按模块分文件）
- **日志轮转**：LogRotationManager 实现自动轮转，单文件最大 10MB，最多保留 5 个归档文件
- **错误日志**：独立 error 级别日志文件

### 配置管理器

- **全局配置**：Ollama 连接、UI 主题/语言、模块启停列表、安全策略、性能参数
- **模块配置隔离**：每个模块独立配置文件，互不干扰
- **变更监听**：onChange 回调机制，配置变更实时通知
- **持久化**：JSON 文件存储在 userData/config/ 目录

### 持久化存储层（SQLite）

- **DatabaseManager**：基于 better-sqlite3，WAL 模式提升并发性能
- **表结构管理**：各模块通过 Repository 模式自行建表和管理
- **备份支持**：BackupManager 实现自动备份（定时触发）和手动备份，保留天数可配置，过期自动清理

### 模块管理器（核心中枢）

- **ModuleScanner**：扫描模块目录，解析 module.json 元数据
- **DependencyResolver**：依赖解析，支持循环依赖检测、缺失依赖告警、版本兼容性检查
- **ModuleValidator**：模块合法性校验
- **ModuleLoader**：模块加载，注入 ModuleContext（事件总线、配置、AI、日志、存储等）
- **ModuleManager**：统一调度扫描→解析→校验→加载的完整生命周期
- **技能搜索路径**：应用根目录 skills + 模块目录 skills + 用户数据 skills + 工作区 skills

### 性能监控

- **PerformanceMonitor**：定时采集 CPU/内存/磁盘/GPU 使用率
- **ResourceCollector**：系统资源数据采集器
- **历史记录**：保留 360 个采样点（5 秒间隔，共 30 分钟）
- **趋势预测**：基于历史数据预测资源使用趋势
- **告警机制**：CPU 80%、内存 85%、磁盘 90%、GPU 90% 阈值告警
- **降频策略**：ThrottleStrategyEngine 实现 aware → degraded → lowPower 三级降频
- **模块资源控制**：ModuleResourceController 按声明的资源限制动态调控模块，支持暂停/恢复

### 轮询注册中心

- **PollingRegistry**：统一管理所有轮询任务，供仪表盘展示
- **两类轮询**：核心轮询（性能监控、自动备份等常驻任务，不绑定模块）+ 模块轮询（绑定 moduleId，模块 deactivate 时自动清理）
- **执行记录**：tickCount 自动累加、lastActivity 模块上报、lastError 错误上报
- **实时推送**：每次变更自动推送到渲染进程，无需前端轮询

### 安全沙箱

- **SandboxManager**：每个模块运行在独立的 utilityProcess 子进程中
- **SandboxIPC**：沙箱 IPC 通信协议，支持请求/响应模式，10s 超时
- **SandboxWorker**：沙箱子进程工作线程
- **逃逸防护**：白名单模式 + API 拦截层，仅允许安全的 Node.js 内置模块（events、util、url、path、crypto、stream 等 13 个），明确禁用 fs、child_process、net、http、vm 等危险模块
- **环境变量白名单**：仅允许 PATH、HOME、LANG、LC_ALL、DISPLAY、APP_ROOT
- **超时控制**：启动超时 10s、初始化超时 15s、优雅关闭超时 5s
- **资源监控**：实时追踪每个沙箱实例的内存和 CPU 使用量

### 能力仲裁器

- **CapabilityRegistry**：能力注册表，支持同名能力多模块注册与去重
- **CapabilityArbiter**：多模块注册同名能力时的仲裁逻辑
- **仲裁优先级**：用户显式指定 > 用户覆盖配置 > priority 字段 > 加载顺序
- **用户覆盖持久化**：用户的选择保存到配置文件，下次启动自动恢复
- **ToolParamSchemas**：为每个模块工具定义 JSON Schema，让 LLM 知道该传什么参数

### AI 调度器

- **OllamaAIService**：封装 Ollama REST API，支持对话（同步/流式）、图片分析、意图识别、嵌入向量
- **AiDispatcher**：意图识别 → 路由分发 → 通用对话的完整调度链路
- **工具调用**：支持 function calling，自动执行工具并返回结果
- **连续失败保护**：连续失败 3 次自动降级到通用对话模式
- **默认模型**：ministral:3b（对话）、qwen2.5-vl（视觉）、nomic-embed-text（嵌入）

### SOUL 管理器

- **SoulManager**：助手人格配置的读取、创建、更新（单例模式）
- **SoulReader**：从 SOUL.md 文件中提取助手名称，兼容开发模式和打包模式
- **存储路径**：`<userData>/config/soul.json`
- **人格配置**：性格标签、说话风格、情感倾向、背景故事、行为准则
- **兼容逻辑**：首次启动检查本地 SOUL.md，有则继承
- **首次引导**：SoulOnboarding 组件引导用户创建助手人格

### 应用框架

- **菜单系统**：createAppMenu 创建原生应用菜单，macOS/Windows 自适应
- **系统托盘**：支持最小化到托盘、右键菜单、窗口显示/隐藏切换

---

## 功能模块（modules/）

### 日程日历（calendar）

- 日程事件的 CRUD 操作（calendar_list/create/update/delete）
- 按年月筛选日程列表
- 支持全天事件和提前提醒设置
- 每分钟自动检查提醒触发
- SQLite 持久化存储

### 剪贴板历史（clipboard-history）

- 剪贴板内容轮询监听（5 秒间隔）
- 历史记录列表查询（clipboard_list）
- 内容固定/取消固定（clipboard_pin）
- 复制历史记录到剪贴板（clipboard_copy）

### 代码片段（code-snippets）

- 代码片段的创建、更新、删除（snippet_create/update/delete）
- 标签管理（创建时可添加标签列表）
- 一键使用：复制到剪贴板并记录使用次数（snippet_use）

### 命令面板（command-palette）

- 全局快捷键 Ctrl+K 呼出
- 模糊搜索命令列表
- 内置命令注册
- 其他模块可动态注册命令
- 最多返回 20 条匹配结果

### 桌面集成（desktop-integration）

- **TrayService**：系统托盘图标、右键菜单
- **HotkeyService**：全局快捷键注册与触发
- **NotificationService**：系统通知弹出
- **AutostartService**：开机自启配置

### 文件操作（file）

- **FileReaderService**：文件读取（文本、二进制）
- **FileWriterService**：文件写入与追加
- **FileWatcherService**：目录变更监听
- 代码高亮预览

### 鼠标键盘控制（input）

- **MouseService**：鼠标移动、点击、拖拽（优先 robotjs，降级 xdotool/osascript/powershell）
- **KeyboardService**：键盘输入、快捷键组合、按键模拟

### 本地知识库（knowledge-base）

- **文件导入**：支持多种文档格式导入（kb_import，自动向量化 + BM25 索引）
- **VectraStore**：自动切片 + 嵌入向量 + BM25 索引
- **混合检索**：向量语义搜索 + BM25 关键词搜索（kb_search，默认混合模式）
- **RAGEngine**：LLM Reranker 重排序 + RAG 问答（kb_ask）
- **DatasetCatalog**：数据集目录浏览
- **DatasetDownloader**：数据集下载管理

### Live2D Cubism 5（live2d-5）

- 基于 Cubism 5 SDK for Web R5 的原生 WebGL 渲染
- 独立窗口运行（400×500 宠物窗口）
- 模型加载与切换
- 表情队列控制（useExpressionQueue）
- 鼠标追踪（useMouseTracking）
- 动画预设系统
- 不依赖 pixi.js，与旧版 Live2D 模块完全隔离

### 记忆系统（memory）

- **MemoryManager**：短期/长期记忆的存储、检索、清理
- **语义搜索**：TF-IDF + 余弦相似度
- **AI 摘要**：调用 Ollama 自动生成记忆摘要
- **自动摘要**：短期记忆达到阈值（默认 50 条）时自动触发压缩摘要
- **SQLite 持久化**：MemoryRepository 管理数据存储

### 多会话管理（multi-session）

- 会话的创建、切换、删除、重命名
- 会话固定（置顶重要会话）
- SQLite 持久化存储

### 通知管理（notifications）

- 系统通知的持久化存储
- 通知查询与筛选
- 已读/未读状态管理
- 监听事件总线自动创建通知

### 主动关怀（proactive）

- **ReminderService**：定时提醒的创建、触发、管理
- **WeatherService**：接入 wttr.in 天气 API，支持天气查询和预报
- 天气预警提醒
- 主动问候

### 快速预览（quick-preview）

- 文件快速预览（不打开编辑器）
- 支持文本、代码、图片等多种格式
- FilePreviewService 统一处理

### 屏幕理解（screen）

- **ScreenCaptureService**：屏幕截图捕获
- **OcrService**：调用 Ollama qwen2.5-vl 视觉模型进行 OCR 文字识别
- 批量 OCR 支持（recognizeBatch）
- 屏幕区域选择

### 技能系统（skill）

- **SkillDiscovery**：技能发现与扫描
- **SkillScanner**：SKILL.md 解析
- **SkillCreator**：技能创建
- **SkillInstaller**：技能安装
- **SkillRefiner**：技能打磨优化
- **SkillChain**：技能链式调用
- **SkillStats**：技能使用统计
- **SkillTransfer**：技能导入导出
- **SkillPersistService**：技能状态持久化
- **三级加载**：应用级 → 模块级 → 用户级

### 系统仪表盘（system-dashboard）

- **SystemInfoService**：获取系统信息
- CPU/内存/磁盘使用率实时展示
- 系统运行时间
- 模块状态总览

### 任务规划（task）

- **TaskPlanner**：复杂任务拆解为多步执行计划（AI 驱动）
- **TaskExecutor**：任务步骤逐步执行
- **TaskService**：任务业务逻辑编排
- 任务 CRUD（task_create/list/delete）
- 任务执行与暂停（task_execute/pause）
- 进度查询（task_progress）
- SQLite 持久化（TaskRepository + TaskStepRepository）

### 主题商店（theme-store）

- 主题列表浏览（theme_list：内置 + 已导入 + 可下载）
- 主题应用（theme_apply：可下载主题自动导入）
- 主题导入/导出（theme_import/export）
- 自定义主题删除（theme_delete，内置主题不可删）
- 明暗模式切换
- 启动时自动恢复上次主题

### 工具路由（tools）

- **ToolRegistry**：工具注册表，支持动态注册
- **ToolRouter**：意图路由，置信度校验
- **ToolExecutor**：工具执行引擎
- 工具执行（tool_execute）
- 工具列表查询（tool_list）
- 意图路由（tool_route）
- 事件驱动：监听其他模块通过事件总线注册的工具

### 翻译面板（translator）

- **TranslationEngine**：翻译引擎（调用 LLM）
- **LanguageDetector**：语言自动检测
- **TranslationService**：翻译历史管理与收藏
- "小希翻译"模式：先查知识库，没找到再调大模型
- 知识库不可用时自动降级到纯 LLM 翻译

### 视觉感知（vision）

- **VisionManager**：视频流捕获与分析
- 开始/停止视觉捕获（vision_start/stop）
- AI 画面分析（vision_analyze，支持 general/text/code 三种模式）
- 帧变化检测（SHA-256 hash 比对）
- 事件驱动：通过事件总线发送帧变化事件

### 工作流自动化（workflow）

- **WorkflowService**：工作流业务逻辑编排
- **WorkflowEngine**：工作流执行引擎
- **WorkflowScheduler**：触发器调度（定时/事件触发）
- 工作流 CRUD（workflow_create/list/delete）
- 工作流执行与暂停（workflow_execute/pause）
- 运行日志查询（workflow_log）
- 内置模板系统（workflow_templates）
- 从模板创建工作流（workflow_create_from_template）
- 运行历史记录（WorkflowRunRepository）

---

## 渲染进程（src/renderer）

### 状态管理（Zustand）

| Store | 职责 |
|-------|------|
| useAppStore | 全局应用状态、当前面板、语言 |
| useChatStore | 聊天消息、流式输出、工具调用 |
| useModulesStore | 模块列表、状态、启停控制 |
| useSettingsStore | 应用设置、Ollama 配置、外观、性能监控参数 |
| useSkillStore | 技能列表、筛选、选中、回收站 |
| useVisionStore | 视觉分析结果、捕获区域 |
| useSoulStore | 助手人格配置状态 |
| useChangesStore | Git 变更文件列表、文件树 |
| useCommandPaletteStore | 命令面板状态、搜索结果 |

### UI 组件

- **聊天面板**：MessageBubble、MessageList、ChatInput、StreamingText（Markdown 渲染）、ToolCallCard、MessageActions
- **Live2D**：Live2DCanvas、Live2DControls、Live2DFallback、Live2DContext
- **设置面板**：SettingsSection、OllamaConfig、ThemeSwitcher、ModelSelector、LanguageSelector、AvatarUploader/Editor、PerformanceMonitorConfig
- **模块管理**：ModuleCard、ModuleDetail、ModuleHeader、ModuleToolbar、ModuleList、ResourceDashboard
- **布局**：MainLayout、Sidebar、Header
- **通用组件**：Button、Toggle、Slider、Modal、Toast、Loading、ErrorBoundary、StatusBar、IconMap
- **通用模块组件**：ModuleHeader、ModuleToolbar、ModuleList（模块复用的基础 UI）
- **命令面板**：CommandPalette（Ctrl+K 呼出）
- **变更面板**：ChangesPanel、FileTree、FilePreview
- **灵魂引导**：SoulOnboarding、SoulIndicator

### 服务层

- **chatService**：聊天服务封装
- **Live2DEasyControlService**：Live2D 简易控制
- **themeEngine**：主题引擎

### 共享类型（src/shared/types/）

| 文件 | 内容 |
|------|------|
| common.ts | DeepPartial、Optional、Prettify 通用工具类型 |
| error.ts | 统一错误码枚举（ErrorCode）+ AppError 错误类 |
| ipc.ts | IPC 通道类型定义（IPCChannels）、ScreenSource、LogEntry |
| soul.ts | SoulConfig、SoulPersonality、SoulCreateRequest、SoulStatus 助手人格类型 |
| index.ts | 统一导出 |

### Hooks

- **useIpc**：IPC 通信封装
- **useTheme**：主题切换
- **useAutoScroll**：聊天自动滚动
- **useAutoContrast**：自动对比度调整

---

## IPC 通道（ipc-handlers/）

| 分类 | 处理器 | 通道 | 说明 |
|------|--------|------|------|
| AI | ai.handlers | ai:chat, ai:chatStream | 对话请求、流式对话 |
| 模块 | module.handlers | module:list/enable/disable/reload | 模块管理，invokeModuleCapability 调用模块能力 |
| 配置 | config.handlers | config:get/set | 配置读写 |
| 文件 | file.handlers | file:read/write/watch | 文件操作 |
| Git+文件 | git-file.handlers | git:status/diff, files:list/read/readAny, files:openPicker, dialog:openFile | Git 操作与文件浏览 |
| 命令面板 | palette.handlers | palette:search/execute/open/close | 命令搜索与执行 |
| 轮询 | polling.handlers | polling:register/registerModule/unregister/update/tick/list | 轮询任务管理 |
| 技能 | skill.handlers | skill:* | 技能管理 |
| 主题 | theme.handlers | theme:* | 主题管理 |
| SOUL | soul.handlers | soul:* | 人格配置 |
| 性能 | performance.handlers | performance:* | 性能监控数据 |
| 热键 | hotkey.handlers | hotkey:register/unregister | 全局快捷键 |
| Live2D | live2d.handlers | live2d:* | Live2D 模型控制 |

---

## 数据安全

- **EncryptionService**：AES-256-GCM 加密/解密，PBKDF2 密钥派生
- **IntegrityChecker**：数据完整性校验
- **BackupScheduler**：定时/手动/配置变更触发备份，cron 表达式调度，文件锁防并发，自动清理过期备份
- **DataExporter**：数据一键导出/导入
- **SecurityManager**：统一安全入口，整合上述四个子系统

---

## 待开发功能（设计阶段）

### 意图识别系统（v1.0 设计）

> 状态：设计阶段 | 硬件：AMD 3800 CPU + 30GB 内存，无 GPU

- **方案**：嵌入向量匹配（nomic-embed-text），CPU 延迟 ~21ms，用户无感
- **IntentMatcher**：获取输入嵌入向量 → 与意图知识库余弦相似度比较 → 置信度 >= 0.75 命中
- **三种学习方式**：
  - 用户主动纠正（最可靠）：UI 反馈按钮，用户指出正确模块
  - 行为隐式学习（最自然）：监听用户手动切换模块行为，与最近输入关联
  - 模块执行反馈闭环：成功 → hitCount++，失败 → 降低置信度
- **预置意图**：chat、vision、search、code、task、proactive、screen、file（8 个）
- **存储**：knowledge.json + vectors-cache.bin + learning-log.json
- **性能预算**：识别 < 50ms，内存增量 < 10MB，启动加载 < 100ms
- **UI**：聊天气泡显示识别结果 + 👍/👎 反馈，设置页意图管理

### 行为分析与自动技能创建（v1.0 设计）

> 状态：设计阶段

- **ActionTracker**：零侵入拦截模块调用，自动参数脱敏（文件路径→扩展名、文本→长度、URL→域名、密码→丢弃）
- **ActionStore**：SQLite 持久化，异步写入队列（50 条批量，5 秒刷盘），保留 30 天自动清理
- **PatternDetector**：滑动窗口 + 频繁序列挖掘，子模式去重（LCS 相似度 > 0.8 合并），置信度综合评分（出现次数 + 长度 + 时间规律性）
- **跨会话模式检测**：会话首尾衔接模式、会话开头习惯性操作
- **SkillSuggester**：检测到模式后自动生成技能建议（名称、描述、工作流步骤）
- **通知冷却**：同一模式忽略后 7 天不再提醒，拒绝后永久不提醒，全局间隔 30 分钟
- **用户交互**：创建技能 / 修改 / 暂时忽略 / 不再提醒
- **性能预算**：行为记录 < 1ms，批量写入 < 10ms，模式检测 1000 条 < 50ms

### 多代理编排系统（v1.0 设计）

> 状态：设计阶段

- **子代理生命周期**：pending → running → done/fail/kill/timeout
- **两种运行模式**：
  - run（一次性）：执行完成即销毁，适合确定性任务
  - session（持久会话）：保持连接，支持多轮交互，适合专用助手
- **任务调度**：自动并行分析 → 拓扑排序 → 同层并行 → 串行依赖
- **通信协议**：主→子（spawn/send/steer/kill），子→主（progress/completed/failed）
- **错误处理**：超时自动终止、异常崩溃隔离、可重试错误重试 1 次
- **资源限制**：最大并发 5 个，单代理最大 200K token，最长 15 分钟
- **安全约束**：子代理不能再创建子代理、不能直接发消息给用户、不能修改安全文件
- **UI**：子代理监控面板、任务分解可视化、子代理详情页
- **开发计划**：核心调度引擎 8h + UI 面板 6h + 持久会话 6h + 高级调度 4h + 历史统计 4h = 约 28h

### Oracle 深度思考（v1.0 设计）

> 状态：设计阶段

- **三档推理强度**：
  - 💡 快速思考：自有提示词增强，无额外延迟
  - 🧠 深度推理：agent-reasoning CoT，2-3x 延迟
  - 🔬 全面分析：agent-reasoning ToT/Refinement，5-10x 延迟
- **架构**：ChatInput 下拉框 → ChatService 传递 oracleMode → IPC → OracleReasoningService
- **OracleReasoningService**：管理 agent-reasoning 代理进程生命周期，检测代理可用性，提供不同模式系统提示词，不可用时降级到 quick
- **文件改动**：useChatStore 新增状态、ChatInput 新增下拉框、chatService 传递参数、新增 oracle-reasoning-service.ts

### 主题系统 v2.0（设计）

> 状态：设计阶段 | 借鉴 shadcn/ui + Chakra UI + Mantine + Ant Design + Radix

- **三层 Token 架构**：Seed Token（7 个值）→ Map Token（自动派生）→ Alias Token（语义化）
- **Seed Token**：primary、background、foreground、border、radius、fontScale、spacingScale
- **暗色模式自动生成**：Mantine primaryShade 算法派生
- **autoContrast 自动对比度**：Mantine 借鉴，确保文字可读性
- **Alpha 透明度色板**：Chakra UI 借鉴，自动生成透明度变体
- **灰度系统**：Radix 12 级灰度刻度
- **Radius 派生**：shadcn/ui 借鉴，从 base radius 自动派生各尺寸
- **迁移策略**：渐进式 4 阶段（基础设施 → 组件适配 → 主题商店升级 → 清理旧代码）

---

## 技术调研报告

### RAG 流程分析（7 步流水线 vs 当前实现）

> 基于 LangChain RAG 标准流程对比，识别缺失项和优化空间

**当前状态**：基础功能 80% 已完成，骨架完整，细节有缺。

**7 步流水线逐项对比：**

| 步骤 | 当前状态 | 说明 |
|------|---------|------|
| 文档加载 | 🟢 MD/TXT/JSON/CSV/YAML/HTML/XML/Parquet/ZIP 完整 | 结构化数据切分是亮点 |
| 文档加载 | 🔴 缺 PDF/DOCX/XLSX | 企业文档 80% 是 PDF，不支持等于 RAG 废了一半 |
| 文本分割 | 🟢 4 种策略 + 智能检测 + overlap | 基础扎实 |
| 向量化 | 🟢 nomic-embed-text via Ollama | 可用 |
| 向量化 | 🟡 embedBatch 串行 | 导入大量文档会很慢 |
| 检索 | 🟢 Top-K 余弦相似度 | 基础可用 |
| 检索 | 🟡 缺相似度阈值过滤、MMR 多样性、混合检索、Reranker | 检索质量有较大提升空间 |
| Prompt | 🟢 系统提示词 + 上下文注入 + 来源引用 | 可用 |
| Prompt | 🟡 硬编码模板，未与 SoulManager 联动 | 可优化 |
| 模型调用 | 🟢 OllamaAIService + 流式输出 + 超时控制 | 可用 |
| 模型调用 | 🟡 无失败重试、无多模型路由 | 可优化 |
| 输出解析 | 🔴 无 OutputParser | 模型返回什么就直接展示，无法保证格式一致 |

**🔴 必须补的（影响核心功能）：**
- PDF 支持（集成 pdf-parse）
- DOCX 支持（集成 mammoth）
- Excel/XLSX 支持（集成 xlsx/SheetJS）
- OutputParser（JSON/Markdown/Citation 解析）
- embedBatch 并行优化（Promise.all + 并发控制）

**🟡 建议优化的：**
- 相似度阈值过滤（score < 0.5 丢弃）
- Prompt 模板可配置
- 失败重试机制（指数退避 3 次）
- 混合检索（向量 + BM25，RRF 融合排序）
- MMR 多样性检索

**🟢 长期目标：**
- Reranker 重排序（需额外交叉编码器模型）
- 多模型路由（简单问题用小模型）
- 语义切分（利用嵌入向量判断语义边界）
- URL 网页导入
- SoulManager 与 RAG 联动（人格化知识库问答）

**LlamaIndex 借鉴方向（不引入库，抄设计）：**
- 关键词索引（BM25）：TF-IDF 或 BM25 关键词检索
- 检索后处理链：过滤 → 重排序 → 压缩 → 去重
- 响应合成模式：compact/refine/tree_summarize 三种模式
- 子问题分解：复杂问题自动拆解为子问题分别检索
- RAG 评估：忠实度/相关性/正确性三个评估指标

---

### QQ 宠物技术架构分析与 Live2D5 借鉴

> 从 QQ 宠物（2005）设计中提取可借鉴思路，指导 Live2D5 桌面宠物开发

**QQ 宠物核心架构：**
- 独立进程（qqpet.exe）+ Flash OCX 控件透明渲染 + HTTP 轮询 + 服务端主导
- 核心循环：时间流逝 → 属性衰减 → 事件触发 → 通知客户端 → 用户互动 → 循环

**属性衰减系统：**
- 饥饿值（每小时 -N）→ 低于阈值 → 饥饿动画
- 清洁值（每小时 -N）→ 低于阈值 → 脏动画
- 心情值（每小时 -N）→ 低于阈值 → 郁闷动画
- 健康值（饥饿+清洁过低时衰减）→ 低于阈值 → 生病
- 成长值（在线时长累积）→ 达到阈值 → 升级
- **关键设计**：离线时也衰减（服务端计算），上线时一次性结算差值

**事件系统：** 定时事件（生日/节日）、触发事件（属性阈值）、随机事件（捡道具）、社交事件（好友互访）

**与 Live2D5 对比：**

| 维度 | QQ 宠物 | Live2D5 | 差距 |
|------|--------|---------|------|
| 渲染 | Flash OCX + 精灵图帧动画 | Cubism 5 SDK + WebGL 实时骨骼 | 我们远超 |
| 窗口 | C++ Win32 不规则透明 | Electron transparent | 持平 |
| 动画 | 预渲染帧序列 | 实时骨骼驱动 + 物理引擎 | 我们远超 |
| 通信 | HTTP 轮询 30-60s | IPC 毫秒级 | 我们远超 |
| 数据 | 服务端主导，关了再开还在 | **无持久化，关了就没了** | 🔴 最大差距 |
| 状态机 | 简单属性阈值触发 | **无状态机** | 🔴 缺失 |
| 交互 | 点击菜单 | 拖拽/点击 + AI 对话 | 我们更强 |
| 对话 | 固定台词 | AI 生成自然语言 | 我们远超 |

**借鉴方案（按优先级）：**

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 属性系统 + 状态机 | hunger/mood/cleanliness/health/intimacy/level，本地持久化 + 离线差值结算 |
| P0 | 气泡对话（AI 驱动） | 根据宠物状态 + 上下文生成自然语言（替代固定台词） |
| P1 | 事件触发动画 | 声明式规则引擎，属性阈值触发动画 + 气泡 |
| P1 | 帧率自适应 | 窗口不可见时降到 5fps，可见时恢复 60fps |
| P2 | 亲密度/成长系统 | 互动累积亲密度，阈值解锁新表情/动作 |
| P2 | 动画队列 + 过渡 | motion group 平滑过渡 |
| P3 | 装扮系统 | Cubism 5 参数控制部位显示/隐藏 |
| P4 | 社交互动 | 局域网/互联网宠物互访 |

**我们的架构优势：**
- AI 对话（自然语言 vs 固定台词）
- 实时骨骼动画（物理引擎 vs 帧序列）
- 本地优先（不依赖服务器）
- 模块热插拔
- WebGL GPU 加速（比 Flash CPU 渲染强 10 倍）

**核心结论**：渲染层我们远超 QQ 宠物，但**状态管理和持久化是最大短板**，是最先要补的。

---

## 开发规范

- 开发内容放在 `desktop/` 目录
- 提交到 `dev` 分支
- 变更记录写入 `desktop/dev-docs/`
- 模块采用 Repository → Service → Module 三层架构
- 遵循 karpathy-guidelines：先想再写、最简优先、精准改动、目标驱动
