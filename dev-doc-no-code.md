Beautiful-Elf 智能桌面助手 - 完整功能介绍方案
前后端分离架构 · 本地优先 · AI 驱动
前端：Electron 41 + React 19 + TypeScript 6 + Three.js r181
后端：FastAPI 0.124 + MySQL 9.5 + Redis 8.6 + Celery 5.6
AI：LlamaIndex + LangChain + LangGraph + Qdrant + Qwen3-Embedding + Qwen3.5

项目概览
Beautiful-Elf 是一款前后端分离的智能桌面助手，采用当前（2026年）最新稳定技术栈构建。前端基于 Electron + React 提供桌面应用交互与 3D 宠物窗口，后端基于 FastAPI + MySQL + Redis + Celery 提供高性能 API、实时推送与异步任务处理。系统深度集成 LlamaIndex + LangChain + LangGraph 构建企业级 RAG 管道，使用 Qdrant 作为向量数据库，Qwen3.5 系列模型提供对话与嵌入能力。数据架构采用存储分层设计：MySQL 存储所有业务数据，Qdrant 仅存储 AI 向量数据，Redis 负责缓存与消息代理，三者通过 ID 关联，职责清晰。技能可动态安装、炼化与链式调用，行为模式检测实现智能化主动建议。

数据架构总览
本项目采用存储分层架构，业务数据与向量数据完全分离，各自使用最合适的存储引擎。

分层原则
MySQL 9.5 - 业务数据唯一真相源
所有 CRUD 业务数据：用户设置、日程、剪贴板、代码片段、对话历史、记忆元数据、技能配置、工作流定义、宠物属性、行为日志、意图配置（文本+元数据）、工具注册、命令注册、性能采样、备份记录等。所有配置统一存 MySQL settings 表，不使用 .env 文件（数据库连接信息除外）。
使用 Alembic 管理 Schema 版本化迁移。
Qdrant - AI 向量数据专用
仅存储需要语义检索的向量：知识库文档分块向量、长期记忆向量、意图嵌入向量。
通过 ID 关联 MySQL 业务数据，不做数据冗余。
向量数据可从 MySQL 重建（重新 embedding），不单独备份。
Redis 8.6 - 缓存 + 消息 + 限流
缓存：MySQL 热数据的缓存（如未来 7 天日程、意图→模块映射结果），TTL 可配置。
消息代理：Celery Broker、WebSocket 消息队列。
限流：API 限流计数器（令牌桶/滑动窗口）。
不存储任何向量数据。
数据关联方式
MySQL 与 Qdrant 通过 ID 关联，查询时先检索 Qdrant 获取向量匹配结果（含 payload 中的业务 ID），再用 ID 去 MySQL 查询完整业务数据。

示例：意图识别 → Qdrant 返回 { intent_id, score } → 用 intent_id 查 MySQL intents 表获取完整配置 → 路由到目标模块。

CQRS 读写分离
采用 Command Query Responsibility Segregation 模式，读写操作分离为独立的 Service 层，各自可独立优化。

Command（写操作）：负责数据的创建、更新、删除，走 CommandService → Repository → MySQL，写入成功后触发事件（如缓存失效、向量同步、WebSocket 广播）。写操作严格校验（Zod / Pydantic），保证数据一致性。

Query（读操作）：负责数据的查询展示，走 QueryService → 可直接读 Redis 缓存 / 只读连接 / 聚合多个数据源。读操作可独立优化（如添加缓存、预计算、物化视图），不影响写入性能。

适用场景：
高频读场景（聊天记录列表、日程展示、技能面板）→ Query 层走 Redis 缓存 + 分页查询。
复杂写场景（知识库导入、工作流执行、意图更新）→ Command 层走 Celery 异步任务。
实时场景（宠物状态、性能监控）→ WebSocket 推送，前端 Zustand 直接更新，不走 Query 层。

实现方式：FastAPI 路由层调用对应的 Service（CommandService / QueryService），Service 内部调用 Repository 操作数据库。前端通过 TanStack Query 的 queryKey 区分读写，写操作成功后自动 invalidate 对应的 queryKey 触发重新查询。

MySQL 核心表结构（概要）
表名	职责	关联
settings	动态配置 KV 存储（所有配置统一存 MySQL，不使用 .env，含 restart_required 标记）	-
conversations	会话列表	-
messages	消息记录（原始对话历史，完整保留）	conversation_id
memory_entries	长期记忆（从对话提炼的摘要+元数据）	-
knowledge_documents	知识库文档元数据	-
knowledge_chunks	知识库文档分块索引（记录 Qdrant 中的向量 ID）	→ Qdrant knowledge_chunks
intents	意图配置（文本+触发词+目标模块+元数据）	→ Qdrant intent_vectors
intent_usage	意图命中统计（hitCount、置信度）	intent_id
skills	技能注册（元数据+启用状态）	→ 文件系统 skills/
skill_stats	技能使用统计（成功率、调用次数）	skill_id
workflows	工作流定义（LangGraph DAG JSON）	-
workflow_runs	工作流运行记录	workflow_id
workflow_step_runs	节点执行详情	run_id
tools	工具注册表（名称、描述、JSON Schema）	-
tool_stats	工具调用统计	tool_id
schedules	日程事件	-
clipboard_items	剪贴板历史	-
snippets	代码片段	-
pet_attributes	宠物六维属性	-
pet_interactions	互动记录（喂食、清洁、聊天）	-
action_logs	行为日志（7天TTL，定时清理）	-
commands	命令注册（内置+模块动态注册）	-
command_usage	命令使用频率（用于智能排序）	command_id
performance_metrics	性能采样数据（360点，约30分钟）	-
soul_configs	助手人格配置	-
backup_records	备份记录（备份时间、文件路径、状态）	-
prompts	Prompt 版本管理（名称、内容、版本号、是否激活）	-
ai_feedback	AI 回答反馈（问题、回答、反馈类型、trace_id）	conversation_id

通用字段说明：所有业务表均包含 deleted（TINYINT，默认 0）软删除标记和 created_at / updated_at 时间戳。查询时自动过滤 deleted = 1 的记录。

索引策略：高频查询字段必须建索引 — messages（conversation_id, created_at）、intents（deleted, enabled）、action_logs（created_at, module）、knowledge_documents（deleted, file_type）、conversations（created_at）、workflow_runs（workflow_id, status）、command_usage（command_id）。复合索引按查询模式组合（如 messages 表的 (conversation_id, created_at) 联合索引）。

数据一致性保障
写入 MySQL 成功后，异步同步向量到 Qdrant（通过 Celery 任务）。
同步失败自动重试 3 次（指数退避），仍失败则告警并记录到修复队列。
删除数据时：采用软删除策略 — MySQL 表统一增加 deleted 字段（TINYINT，默认 0），删除操作仅将 0 → 1，不物理删除数据；同时将 Qdrant 对应向量的 payload 中标记 deleted: true。查询时自动过滤 deleted = 1 的记录，向量检索时也过滤 payload.deleted。物理清理由定时任务每月执行一次（需二次确认）。
更新数据时：先更新 MySQL → 触发重新 embedding → 更新 Qdrant 向量。
备份策略
MySQL：Celery Beat 定期 mysqldump 备份，保留最近 15 天。
Redis：持久化（AOF + RDB），丢失后可从 MySQL 重建缓存。
Qdrant：不单独备份，丢失后可从 MySQL 重新 embedding 重建。

技术栈全景
类别	技术	版本	用途
前端桌面	Electron	v41.0.0	应用容器、系统 API、独立宠物窗口
UI 框架	Ant Design	v6.4.2	组件库、主题系统、图标
前端框架	React	v19.2.6	UI 渲染
语言	TypeScript	v6.0	类型安全
构建工具	electron-vite	v3.0.0+	构建、ESM、热更新
3D 引擎	Three.js + @react-three/fiber + @react-three/drei	r181 + v9.6.0 + v9.118.0	桌面宠物渲染、场景管理
物理引擎	ammojs-es	最新	PMX 模型刚体模拟
状态管理	Zustand + TanStack Query	v5.0.12 + v5.100.13	客户端状态、服务端缓存
HTTP/表单	Axios + React Hook Form + Zod	v1.16.0 + v7.76.0 + v4.3.6	网络请求、表单、全栈校验
日志	electron-log	v5.x	分级日志、自动轮转
长列表优化	react-window	v1.x	虚拟滚动（聊天记录）
代码片段编辑	react-codemirror	最新	轻量级代码编辑器
PDF 预览	pdf.js	最新	文件预览
OCR 识别	Tesseract.js	最新	纯前端文字识别
剪贴板管理	集成成熟 Electron 剪贴板管理器方案	-	历史记录、固定、搜索
打包/更新	electron-builder + electron-updater	v26.9.0 + v4.3.9	多平台打包、自动更新
测试	Vitest + @testing-library/react	v4.1	单元/集成测试
代码规范	ESLint + Prettier + @typescript-eslint	v10.2.1 + v3.8.2	前端代码质量
Git 规范	Husky + lint-staged + commitlint	v9.1.0 + v16.4.0 + v21.0.1	Git hooks、提交规范
后端框架	FastAPI + Uvicorn	v0.124.0 + v0.47.0	异步 API、WebSocket
数据库	MySQL	v9.5.0	关系数据持久存储
异步驱动	aiomysql	v0.3.2	非阻塞数据库访问
ORM	SQLAlchemy	v2.0.46	数据库 ORM
迁移工具	Alembic	v1.18.1	Schema 版本化管理
缓存/消息	Redis	v8.6.0	缓存、消息代理、限流
任务队列	Celery	v5.6.0	异步任务、定时任务、工作流编排
配置管理	Pydantic Settings	v2.12.0	配置校验与类型安全（数据存 MySQL settings 表）
数据验证	Pydantic	v2.12.5	请求/响应数据校验
反向代理	Nginx	v1.30.0	服务器部署模式使用（可选）
高性能计算	Rust + PyO3 + maturin	最新	批量向量相似度、pHash、LCS
代码规范	Ruff	v0.9.0	Python 代码检查与格式化
AI 能力	Ollama	最新	本地大模型服务
对话模型	Qwen3.5 (Ollama)	最新	通用对话、工具调用
嵌入模型	Qwen3-Embedding (Ollama)	最新	文本向量化
RAG 管道	LlamaIndex + LangChain + LangGraph	最新	文档索引、检索、多跳推理
向量数据库	Qdrant	最新	高性能本地/远程向量检索
视觉模型	llava (备用)	最新	图像分析（可选）

一、项目工程化
能力	技术实现	说明
构建与热更新	electron-vite	支持主进程、渲染进程、预加载脚本的 HMR
代码规范	ESLint + @typescript-eslint + Prettier	统一代码风格，集成于 IDE 和 Git hooks
Git 工作流	Husky + lint-staged + commitlint	提交前自动格式化、校验提交信息
提交规范	conventional-commits（feat/fix/docs/refactor）	提交信息格式化，配合 commitlint 强制校验
变更日志	standard-version / changesets	基于 conventional-commits 自动生成 CHANGELOG.md，每次发版自动更新
单元/集成测试	Vitest + @testing-library/react	组件测试、Hook 测试、API 集成测试
日志记录	electron-log	按模块分文件输出，支持日志轮转（10MB/5个）
打包与更新	electron-builder + electron-updater	多平台打包，增量自动更新
性能监控（开发）	Stats.js	实时显示 FPS、MS、MB
API 版本化	APIRouter prefix（/api/v1/）	所有接口统一版本前缀，旧版本设废弃时间表，新版本并行运行，客户端按版本调用
二、核心基础设施
2.1 事件总线
实现：基于 Node.js EventEmitter 封装全局事件总线，支持 on、off、emit、once。

模块级隔离：每个模块在 module.json 中声明 provides（发出的事件）和 consumes（监听的事件），未声明的事件自动拦截并记录错误日志。

错误隔离：单个事件处理器的异常不影响其他处理器，错误通过 _error 事件独立上报。

2.2 日志系统
前端：electron-log，按模块输出到独立文件（如 chat.log、pet.log），支持 debug/info/warn/error 四级。

后端：Python logging + Uvicorn 访问日志，输出到 logs/ 目录，支持 JSON 格式（便于日志聚合）。

结构化日志字段：每条日志统一携带 trace_id（请求链路 ID）、user_id、session_id、module、level、timestamp，支持按维度聚合查询。trace_id 在前端发起请求时生成，跨 API → Celery → Qdrant 全链路透传。

敏感数据脱敏：日志中自动对 API Key、Token、用户消息内容做脱敏处理（保留前后几位，中间用 *** 代替）。

日志轮转：单文件最大 10MB，最多保留 5 个归档，过期自动清理。

2.3 健康检查端点
存活检查（/health）：返回服务是否存活，供进程管理器和负载均衡器探活。

就绪检查（/ready）：检查所有依赖是否可用（MySQL 连接、Redis 连接、Qdrant 连接、Ollama 服务），任一不可用返回 503。

依赖状态（/deps）：返回各依赖的详细状态（连接延迟、版本号、连接池使用率），供运维监控和排查。

2.4 WebSocket 通信层
连接管理：后端通过 FastAPI WebSocket 端点维护长连接，支持多客户端同时连接（主窗口、宠物窗口等）。

心跳检测：客户端每 30 秒发送 ping，服务端回复 pong。若连续 3 次未收到 pong，客户端判定断线。

断线重连：客户端实现指数退避重连策略（初始 1 秒，最大 30 秒，抖动因子 0.5），重连成功后自动同步离线期间的变更事件。

消息格式：统一 JSON 格式 `{ "type": "事件类型", "payload": {...}, "timestamp": 1234567890 }`，支持的事件类型包括 config_update、notification、pet_state、workflow_progress、subagent_status 等。

连接池上限：单实例最多维护 10 个 WebSocket 连接，超出时拒绝新连接并通知客户端。

2.5 设置系统（全局配置管理中心）
设置系统是 Beautiful-Elf 的配置中枢，统一管理应用、AI、模型、界面等所有可配置项。前端使用 Ant Design Form + Tabs 分区展示，所有配置统一存储在 MySQL settings 表，启动时加载到内存，运行时通过 API 读写。

2.5.1 Ollama 配置
Ollama 服务地址：可配置本地地址（默认 http://localhost:11434）或远程服务器地址，支持 HTTP/HTTPS。配置存储在 MySQL settings 表，修改后后台立即更新 settings 表中对应的地址字段，其他服务（如对话、嵌入）直接读取该字段，无需重启。

扫描本地大模型：前端调用后端 API /api/v1/ollama/models，返回 Ollama 中已下载的模型列表（如 qwen3.5:7b、qwen3-embedding:latest、llava:latest）。

模型选择：

对话模型：从扫描到的模型中选择一个作为默认对话模型（推荐 qwen3.5:7b 或 qwen3.5:14b）。

嵌入模型：选择用于 RAG 和意图识别的嵌入模型（推荐 qwen3-embedding）。

视觉模型：可选，用于 OCR 辅助或图像分析（如 llava）。

测试连接：提供"测试连接"按钮，调用 Ollama 的 /api/v1/ollama/tags 接口，验证地址正确且服务可用，失败时给出明确错误提示。

模型下载管理（高级）：可展示已安装模型列表，并提供一键下载新模型（通过 Ollama CLI 或 API 异步拉取）。

2.5.2 AI 设置
模型温度 (Temperature)：滑块范围 0.0～2.0，步长 0.1，控制生成内容的随机性。默认 0.7。

最大生成长度 (Max Tokens)：数字输入框，范围 1～8192，默认 2048。控制单次回答的最大长度。

Top-P：范围 0.0～1.0，默认 0.9。核采样参数。

频率惩罚 / 存在惩罚：可选，用于减少重复。

AI 头像：用户可上传自定义头像（支持 JPG/PNG），用于聊天界面中 AI 助手的头像显示。头像存储在后端用户数据。

系统提示词：可编辑全局系统提示词（如"你是一个可爱的桌面助手"），或针对不同模块单独配置。

2.5.3 应用设置
语言：当前支持简体中文，后续根据需要扩展国际化支持。

开机自启：开关控制 Electron 是否开机启动。

启动时最小化到托盘：开关。

关闭主窗口行为：退出应用 / 最小化到托盘。

2.5.4 宠物设置
宠物模型选择：模型路径设置-设置保存后台，列出后台返回的模型列表  后台去读取设置的路径目录下的 .pmx 文件，用户可切换不同模型。

宠物窗口设置：透明度、是否置顶、窗口尺寸（预设 400×500，可自定义）。

属性衰减速度：可选"慢 / 正常 / 快"，影响饥饿、清洁等属性的每小时衰减值。

气泡对话频率：控制宠物自动说话的间隔（30 秒～5 分钟）。

2.5.5 快捷键设置
全局快捷键映射：用户可自定义"打开主窗口"、"打开命令面板"、"截图"等快捷键。

冲突检测：保存时检测是否与其他全局快捷键冲突，并提示。

2.5.6 隐私与安全
数据加密：是否对本地存储的敏感配置（如 API Key）加密（默认开启）。

日志级别：可动态调整日志记录级别（Debug / Info / Warn / Error）。

匿名使用统计：可选是否允许收集匿名使用数据（用于改进）。

2.5.7 关于与更新
版本信息：展示前端、后端、关键依赖版本（从 MySQL settings 表读取）。

检查更新：手动触发 electron-updater 检查更新。

更新日志：从更新服务器拉取变更记录展示。

技术实现：

所有配置统一存储在 MySQL settings 表（KV 结构），不使用 .env 文件（数据库连接信息除外）。启动时从 MySQL 加载全部配置到内存，运行时直接读取内存配置。

前端修改配置 → 调用 API /api/v1/config → 后端更新 MySQL settings 表 + 刷新内存配置 → 通过 WebSocket 广播配置变更事件 → 其他客户端同步更新。

首次启动时 MySQL 为空，使用代码中的默认值初始化 settings 表。配置项分为两类：热更新配置（修改后即时生效，如 AI 参数、主题、快捷键、Ollama 地址）和需重启配置（如数据库连接信息），settings 表中通过 restart_required 字段标记。前端修改需重启的配置时，自动弹出提示"此配置需要重启应用/模块才能生效"，用户可选择立即重启或稍后手动重启。

数据库连接信息（MySQL、Redis、Qdrant 地址）作为唯一例外，通过环境变量或命令行参数传入（因为这些是 MySQL 本身的依赖，不能从 MySQL 读取自身连接信息）。

数据库连接池配置：SQLAlchemy 连接池大小默认 10，最大 overflow 20，连接超时 30 秒，连接回收时间 3600 秒（防止 MySQL 端超时断开）。Redis 连接池 max_connections 默认 20。连接池使用率通过 /deps 健康检查端点暴露，超过 80% 触发告警。

三、AI 智能核心
所有 AI 能力基于 Ollama 本地模型 + LlamaIndex/LangChain/LangGraph 编排，Qdrant 作为向量数据库，实现企业级 RAG 管道。

3.1 对话与意图识别
聊天接口：FastAPI 提供 /api/v1/ai/chat（非流式）和 /api/v1/ai/chatStream（WebSocket 流式）。

对话模型：使用 Ollama 运行的 Qwen3.5（7B/14B/32B 可选），支持函数调用（Function Calling）和工具使用。

AI 护栏（Guardrails）：
输入侧：敏感词过滤（维护敏感词库，命中则拦截并提示用户）、Prompt 注入检测（识别"忽略之前的指令"等模式，命中则拒绝并记录日志）、输入长度限制（防止超长输入耗尽资源）。
输出侧：回答长度校验（超长则截断并提示）、有害内容检测（调用安全分类模型，命中则拦截并返回默认回答）、格式校验（如工具调用结果必须是合法 JSON）。

用户反馈闭环：每次 AI 回答底部提供 👍/👎 按钮，👎 时弹出可选的原因标签（不准确/不相关/有害/其他）+ 自由文本输入。反馈记录存入 MySQL（含问题、回答、反馈类型、trace_id），定期分析差评模式用于优化 Prompt 和 RAG 策略。

意图识别流程：

用户输入文本 → 调用嵌入模型 Qwen3-Embedding 生成向量。
去 Qdrant intent_vectors Collection 做相似度搜索（Rust 加速批量余弦计算）。
返回 top-1 结果（含 payload 中的 intent_id 和 score）。
最高置信度 ≥ 0.75 则命中意图，用 intent_id 查询 MySQL intents 表获取完整配置，路由到对应模块的工具。
意图冲突处理：当 top-1 与 top-2 的置信度差值 < 0.1 时（如 0.82 vs 0.78），判定为意图冲突，不自动路由，而是触发澄清对话（如"你是想查天气，还是设置日程？"），展示 top-2 意图供用户选择。用户选择后记录到 intent_usage 表用于后续优化。
未命中则进入通用对话模式，可触发 RAG 检索或工具调用。
性能优化：Redis 缓存高频意图文本→模块的映射结果（TTL 1 小时），避免重复向量检索。意图被用户纠正或置信度变化时，主动删除对应 Redis 缓存 key（不等 TTL 过期），确保下次请求使用最新数据。批量相似度计算使用 Rust + PyO3 扩展。

LLM 语义缓存：对通用对话（非意图命中、非工具调用）启用语义缓存 — 用户提问先生成 embedding，与 Redis 中已缓存的问题向量做相似度比较，距离 < 0.05 则直接返回缓存回答（跳过 Ollama 推理），TTL 24 小时。命中缓存时前端显示"⚡ 快速回答"标识。仅对事实性问题启用，创意/生成类问题自动跳过缓存。

Prompt 版本管理：系统提示词、意图模板、技能提示词统一存入 MySQL prompts 表（含 name、content、version、is_active、created_at）。修改 Prompt 时创建新版本而非覆盖旧版，支持一键回滚到历史版本。前端设置页面展示 Prompt 版本列表，可对比差异。A/B 测试：可对同一 Prompt 配置多个版本，按用户或比例分配，收集效果数据后选择最优版本。

3.2 RAG 知识库系统（LlamaIndex + LangChain + LangGraph + Qdrant）
这是本项目的核心 AI 能力，采用业界最先进的 RAG 技术栈。

文档导入与索引（LlamaIndex）：

支持格式：PDF、DOCX、MD、TXT、JSON、CSV、YAML、HTML、XML、ZIP。

使用 LlamaIndex 的 SimpleDirectoryReader 加载文档。分块策略采用 LlamaIndex 的 SemanticSplitterNodeParser（基于嵌入模型的语义分块），它会根据文本语义边界自动决定分块大小，而非固定切割。对于 Markdown 文档优先按标题层级分块，代码文件按函数/类边界分块。可选配置：buffer_size（语义块之间的缓冲区大小，默认 1）、breakpoint_percentile_threshold（语义断点阈值，默认 95）。保留 fallback 策略：若语义分块失败（如嵌入服务不可用），降级为 RecursiveCharacterTextSplitter（块大小 512，重叠 100）。

使用 Qwen3-Embedding 将每个块向量化，存储到 Qdrant knowledge_chunks Collection（本地模式），payload 中记录 doc_id 和 chunk_index。

文档元数据（文件名、导入时间、块数、文件类型）存入 MySQL knowledge_documents 表，便于管理和展示。Qdrant 中的 doc_id 与 MySQL 中的 id 一一对应。

检索与生成（LangChain + LangGraph）：

混合检索：Qdrant 支持向量 + 关键字全文搜索，可配置权重（默认 0.7 向量 + 0.3 关键字）。

重排序：使用 CrossEncoder 模型（可选）对召回结果精排。

LangGraph 多跳推理：对于复杂问题，自动拆解为多步检索（如"先查 A 概念，再查 B 关联"），使用 LangGraph 状态机管理推理链。

流式回答：通过 WebSocket 逐 token 返回，同时携带来源引用。

知识库管理：

DatasetCatalog：前端表格展示已导入文档（数据来自 MySQL knowledge_documents 表，自动过滤 deleted = 1 的记录），支持按类型、时间筛选、删除。删除采用软删除：MySQL knowledge_documents.deleted → 1，同时将 Qdrant 对应向量 payload 标记 deleted: true。支持"回收站"功能，可恢复误删文档。

DatasetDownloader：导出知识库为 JSON（包含 MySQL 元数据 + Qdrant 向量快照），便于备份迁移。

3.3 工具注册与调用（LangChain Tools）
ToolRegistry：统一注册表，工具注册信息持久化到 MySQL tools 表（名称、描述、JSON Schema、所属模块），启动时加载到内存。调用统计数据（调用次数、成功率、平均耗时）记录到 MySQL tool_stats 表。

工具实现：每个工具用 LangChain @tool 装饰器定义，自动生成 JSON Schema。

工具调用流程：用户问题 → LLM 决策 → 自动调用对应工具 → 结果返回 LLM → 生成最终回答。

工具示例：查询天气、创建日程、搜索知识库、控制宠物等。

3.4 记忆系统（短期 + 长期 + 语义）
短期记忆：会话内消息历史（前端 Zustand 存储，不持久化）。

对话历史：MySQL conversations 表存储会话列表，messages 表存储每条消息的完整记录（角色、内容、时间戳、工具调用等）。这是原始数据，完整保留，不向量化。

长期记忆：MySQL memory_entries 表存储从对话中提炼的摘要和关键信息（非原始消息）；重要记忆片段向量化后存入 Qdrant memory_vectors Collection，payload 中记录 memory_id 和 conversation_id，与 MySQL 通过 ID 关联。

语义检索：用户提问时，同时检索 Qdrant knowledge_chunks 和 memory_vectors 两个 Collection，实现知识库+跨会话记忆的联合检索，结果用 ID 回查 MySQL 获取完整上下文。

自动摘要：Celery 定时任务调用 Qwen3.5 对每日对话历史（messages 表）生成摘要，摘要文本存入 MySQL memory_entries，同时 embedding 后写入 Qdrant。原始对话记录不受影响。

3.5 灵魂系统（Soul）
人格配置：每个助手拥有独立的 SOUL.md 文件，定义性格标签、说话风格、情感倾向、背景故事、行为准则。

SoulManager：后端管理助手人格的 CRUD，MySQL 持久化。

首次引导：使用 Ant Design Steps 组件引导用户创建专属助手人格（名称、头像、性格选项）。

运行时使用：对话时注入人格系统提示词，使 LLM 输出符合角色设定。

3.6 翻译模块
术语优先翻译：检索知识库中的术语表（专业词汇），若命中则直接返回翻译结果；若未命中则提示"无资料支持"，不调用 LLM。

RAG 增强翻译：检索知识库中的术语表，若命中则直接使用专业译法；若未命中则调用 Qwen3.5 进行通用翻译。

四、桌面效率工具
4.1 日程模块
前端：@ant-design/calendar + date-fns，支持月/周/日视图。

CRUD：使用 React Hook Form + Zod 校验表单（标题、时间、全天事件、提前提醒时间）。

提醒：后端 Celery Beat 定时任务（每分钟扫描），触发时通过 WebSocket 推送，前端 Electron Notification 弹窗。

数据存储：MySQL 存储日程事件，Redis 缓存未来 7 天的事件用于快速展示。日程变更时通过写穿透策略同步更新 MySQL 和 Redis 缓存（写入 MySQL 成功后立即清除对应 Redis 缓存，下次读取时重新加载）。

4.2 剪贴板模块（集成成熟方案）
实现方式：不重复造轮子，直接集成 Electron 生态中成熟的剪贴板管理器代码库electron-clipboard-manager。

核心能力：

监听剪贴板变化（使用 clipboard-event-emitter 替代轮询，事件驱动）。

支持内容固定（Pin）、搜索、一键复制。

前端 UI：Ant Design List + 虚拟滚动，右键菜单删除。

4.3 代码片段模块（轻量级编辑器）
编辑器：使用 react-codemirror（基于 CodeMirror 6），体积小（约 250KB），支持 100+ 语言语法高亮、主题、自动补全。

标签管理：Ant Design Tag + Select 多选标签。

使用统计：MySQL 记录使用次数，高频片段排序靠前。

CRUD：FastAPI 接口 + 前端表单。

4.4 命令面板
UI 组件：使用 Ant Design AutoComplete 实现，浮层展示匹配结果。

触发：全局快捷键 Ctrl+K（Electron globalShortcut + IPC）。

命令来源：内置命令（打开设置、切换主题、打开宠物窗口、截图等） + 模块动态注册。所有命令注册信息存 MySQL commands 表。

智能排序：按使用频率（MySQL command_usage 表记录每次执行） + 匹配度排序，最多显示 20 条。

4.5 提醒与天气
提醒服务：用户可设置一次性或重复提醒（每天/每周），后端 Celery Beat 调度，前端 Electron Notification 弹窗。

天气服务：FastAPI 调用 wttr.in 或 open-meteo 免费 API，Redis 缓存（30 分钟），支持当前天气 + 未来 3 天预报。

主动问候：根据时间和天气，AI 生成个性化问候语（如"早上好！今天有雨，记得带伞"）。

4.6 文件预览
支持格式：文本（.txt）、代码（.js/.py/.html 等）、图片（.jpg/.png）、PDF。

实现：

文本/代码：react-codemirror 只读模式展示。

图片：Ant Design Image 组件预览。

PDF：pdf.js 渲染第一页缩略图或完整文档。

入口：在聊天窗口点击文件链接、或在文件管理器中选择"用 Beautiful-Elf 预览"。

4.7 OCR 识别（纯前端 Tesseract.js）
截图：Electron desktopCapturer 捕获整个屏幕或选定区域（绘制 Canvas 选区）。

识别：直接在前端使用 Tesseract.js 进行文字识别，无需上传后端。

支持中文简体、英文等多语言。

通过 Web Worker 处理，不阻塞 UI。

优势：数据完全本地处理，隐私安全；响应速度快，离线可用。

历史记录：识别结果存储到 MySQL（可选），前端表格展示。

五、3D 桌面宠物
基于 Three.js 生态实现高性能、低资源占用的桌面宠物，支持 PMX 模型（MMD 模型格式）。

在宠物窗口的 blur、hide、close 事件中，主动调用 renderer.dispose() 和 scene.clear()，并设置 null 以便垃圾回收。

同时，当宠物窗口不可见时，停止动画循环（cancelAnimationFrame），节省 CPU/GPU。

5.1 渲染引擎
3D 库：Three.js r181 + @react-three/fiber（声明式 React 组件）。

辅助组件：@react-three/drei 提供灯光、环境、性能监控等。

模型加载：使用 Three.js 官方 MMDLoader 加载 .pmx 模型文件及 .vmd 动作文件。

物理模拟：ammojs-es 处理模型内置刚体（头发、衣物、饰品的物理飘动）。

独立窗口：Electron BrowserWindow 配置 transparent: true、frame: false、alwaysOnTop: true，尺寸 400×500。

性能优化：窗口不可见时帧率降至 5fps，可见时恢复 60fps；支持多模型切换。

5.2 宠物状态系统
属性（后端 MySQL pet_attributes 表存储）：

🍖 饥饿值：每小时衰减 5%，低于 30% 触发饥饿动画。

🧹 清洁值：每小时衰减 3%，低于 40% 触发脏动画。

😊 心情值：每小时衰减 2%，低于 20% 触发郁闷动画。

❤️ 健康值：饥饿+清洁双低时联动衰减。

💕 亲密度：互动（喂食、清洁、聊天）累积，解锁新表情/动作。

⭐ 等级：成长值累积升级。

状态机：声明式 JSON 规则（如 { "hunger": "<30", "action": "hungryAnimation", "bubble": "我好饿..." }），前端监听属性变化触发。

离线差值结算：宠物窗口关闭时记录时间戳，重新打开时根据离线时长计算属性衰减，一次性更新。各属性最低衰减至 10%，不会因长时间离线而归零。

AI 气泡对话：根据当前状态（低饥饿、高亲密度等）调用 Ollama 生成自然语言，显示在宠物头顶（Ant Design Popover）。

5.3 动画与交互
内置动画：待机、走路、跳跃、喂食、清洁、生病等，使用 .vmd 动作文件。

表情：通过 PMX morph（变形器）实现眨眼、微笑、伤心等表情。

鼠标追踪：监听宠物窗口的 mousemove 事件，计算头部骨骼旋转角度（IK 可选用 MMDAnimationHelper）。

交互事件：点击宠物弹出属性面板（Modal），拖拽宠物窗口移动（-webkit-app-region: drag）。

六、智能化扩展
6.1 意图学习系统
用户主动纠正：当路由错误时，用户可通过反馈按钮（Ant Design Rate）选择正确模块，系统记录并更新意图向量。

隐式学习：监听用户手动切换模块的行为（如说"天气"却点了日程模块），自动关联意图并调整置信度。

向量更新：后台 Celery 任务将更新后的意图文本重新 embedding，写入 Qdrant intent_vectors Collection，同步更新 MySQL intents 表的元数据。使用 Rust 加速批量余弦相似度计算。

结果反馈闭环：模块执行成功 → MySQL intent_usage 表中 hitCount++，同时更新 Qdrant 对应向量的 payload；执行失败 → 降低置信度，避免再次误判。意图更新时主动清除 Redis 中对应的缓存 key。

6.2 行为模式检测与技能自动建议
ActionTracker：零侵入拦截所有模块调用，记录行为序列（自动脱敏敏感参数）。

脱敏规则：文件路径 → 扩展名；文本 → 长度；URL → 域名；密码 → 丢弃。

存储：MySQL 持久化行为日志，Redis 异步写入队列（1 秒刷盘，进程退出时 flush），保留 7 天自动清理。

默认关闭行为模式检测，用户主动启用时才记录。

同时提供"一键清除所有行为数据"按钮。

PatternDetector：

滑动窗口（窗口大小 5）提取用户操作序列。

使用 Rust + PyO3 加速 LCS（最长公共子序列）相似度计算，相似度 > 0.8 则合并为模式。

支持跨会话模式检测（如每天上班后先看日程再查天气）。

SkillSuggester：

检测到模式后，调用 LLM 生成技能建议（名称、描述、工作流步骤）。

前端通过 Ant Design Notification 提示用户："发现您经常在查看日程后查询天气，是否创建'工作前准备'技能？"

用户可选择创建、修改、忽略、不再提醒。

通知冷却：同一模式忽略后 7 天不再提醒，全局间隔 30 分钟。

6.3 技能系统（可动态扩展与炼化）
技能发现：扫描 skills/ 目录下的 SKILL.md 文件（YAML Front Matter 描述元数据：名称、版本、依赖、触发词）。

技能安装：

从 GitHub 仓库或本地压缩包导入技能（.skill 文件）。

后端解压到 skills/ 目录，并注册到数据库。

启用/禁用：前端 Card + Switch 控制，状态持久化到 MySQL skills.enabled 字段，禁用时不再参与意图路由。

技能炼化（Refine）：

用户可选中一个已安装技能，点击"炼化"按钮。

后端从 MySQL skill_stats 表读取该技能的使用统计数据（成功率、调用次数、平均耗时），调用 LLM 分析并生成优化建议（如改进描述词、调整参数默认值）。

用户可编辑 SKILL.md 或代码实现，提交后重新加载。

生成新技能：

用户通过自然语言描述需求（如"每天晚上八点提醒我喝水"）。

后端调用 LLM 生成完整技能代码（工具函数 + SKILL.md），自动安装。

6.4 子代理系统（LangGraph 原生支持）
实现：使用 LangGraph 构建多代理系统，每个子代理是一个 LangGraph 节点。

生命周期：主代理根据任务复杂度动态创建子代理，子代理可独立运行并返回结果。

调度：FastAPI + Celery 执行子代理任务，支持并行和依赖。

监控：前端 WebSocket 接收子代理执行步骤（Ant Design Timeline 展示）。

运行中子代理管理面板：前端展示当前所有运行中的子代理列表（Ant Design Table），包含子代理 ID、任务名称、状态（运行中/暂停/已完成）、已运行时间、当前步骤。每个子代理行提供"终止"按钮（Ant Design Popconfirm 确认），点击后通过 WebSocket 发送终止指令，LangGraph 立即中断该子代理的执行并清理资源。支持一键终止所有运行中的子代理。

6.5 工作流模块
工作流定义：使用 LangGraph 的 StateGraph 定义工作流 DAG，节点可以是工具、技能或子代理。

触发方式：

手动触发：用户在前端点击"执行"。

定时触发：Celery Beat 调度。

事件触发：监听事件总线（如文件变化触发处理工作流）。

执行引擎：Celery 任务队列执行 LangGraph 编译后的可执行图。运行记录存 MySQL workflow_runs 表，每个节点的执行详情（状态、耗时、输入输出）存 MySQL workflow_step_runs 表。

模板系统：预置常用工作流模板（如"文档处理"：PDF 导入 → 向量化 → 生成摘要），用户可一键创建。

运行监控：实时展示每个节点的状态、耗时、输出，支持暂停/重试。

6.6 视觉模块
屏幕捕获：Electron desktopCapturer 获取视频流，支持选区捕获。

帧变化检测：使用 pHash（感知哈希）算法，每帧计算哈希值，与上一帧比较差异比例。

Rust + PyO3 加速哈希计算，变化阈值可配置（默认 5%，范围 1%～20%）。根据活动窗口类型自动调整敏感度：代码编辑场景阈值较低（3%，因为代码变化小但重要），视频/游戏场景阈值较高（15%，减少无效捕获）。用户也可在设置中手动调整。变化超过阈值才发送后端。

AI 分析：可选调用 Ollama llava 模型（用户授权后），支持三种分析模式：

general：描述画面内容。

text：提取截图中的文字。

code：识别截图中的代码并解释。

主动推送：用户可设置"当屏幕出现特定内容时提醒"（如"检测到错误弹窗"），通过事件总线触发。

6.7 推理深度（Oracle）
三档模式（前端 Segmented 切换）：

快速思考：标准提示词，无额外延迟（适合日常对话）。
深度推理：启用思维链（CoT），2-3 倍延迟（适合逻辑推理题）。
全面分析：启用思维树（ToT） + 自我反省（Refinement），5-10 倍延迟（适合复杂规划）。
后端实现：不同模式对应不同的 LangChain 提示词模板和参数（如 temperature、max_tokens）。

降级策略：若用户问题简单，即使选择深度模式也自动降级为快速模式（通过检测关键词）。

七、系统与安全
7.1 性能监控系统
数据采集：后端使用 psutil 每分钟采集 CPU、内存、磁盘、GPU（如有）使用率，并存储到 MySQL（保留 360 个采样点，约 30 分钟趋势）。

实时推送：通过 WebSocket 每 5 秒推送最新数据到前端。

前端展示：Ant Design Progress + 自定义图表（echarts）实时显示。

告警机制：CPU > 80%、内存 > 85%、磁盘 > 90% 时触发告警（前端通知 + 日志）。

趋势预测：基于历史数据线性回归预测未来 10 分钟的使用率（仅展示，不自动操作）。

7.2 轮询管理
前端轮询注册表：PollingRegistry 统一管理所有轮询任务（如天气刷新、剪贴板监听、性能数据拉取）。

核心轮询：性能监控、自动备份等常驻任务。

模块轮询：模块可注册自己的轮询任务，绑定模块生命周期（模块禁用时自动停止）。

后端任务调度：Celery Beat 统一管理定时任务（日程提醒、记忆摘要、数据备份等）。

7.3 错误处理与容错
前端错误边界：每个功能模块用 React ErrorBoundary 包裹，模块崩溃时显示友好的错误卡片（含"重新加载"按钮），不影响其他模块和主界面。全局兜底 ErrorBoundary 捕获未处理异常，上报错误日志并提示用户。

后端异常处理：FastAPI 注册全局异常处理器（exception_handler），统一捕获所有未处理异常，返回标准错误格式 `{ "code": 500, "message": "...", "request_id": "..." }`。业务异常（如参数校验失败、权限不足）使用自定义 HTTPException 子类，返回对应的 HTTP 状态码和错误信息。

WebSocket 错误恢复：WebSocket 连接异常断开时，客户端按指数退避策略自动重连（见 2.3 节）。服务端 WebSocket handler 包裹 try/except，单个连接的异常不影响其他连接。

7.4 安全系统

备份调度：Celery Beat 每 3 天凌晨自动执行 mysqldump 备份 MySQL，保留最近 15 天备份，备份记录（时间、文件路径、状态）存 MySQL backup_records 表。Redis 开启 AOF + RDB 持久化。Qdrant 向量数据不单独备份（可从 MySQL 重新 embedding 重建）。

数据导出/导入：用户可导出所有个人数据（JSON 格式，包含 MySQL 业务数据），或从备份恢复。恢复后自动触发 Qdrant 向量重建任务。

前端安全基线：

contextIsolation: true、nodeIntegration: false。

配置 CSP（内容安全策略）限制脚本来源。

禁用 webSecurity 仅限开发模式。

7.5 系统服务
系统托盘：Electron Tray + Menu，支持显示/隐藏主窗口、退出应用。

全局快捷键：globalShortcut 注册（如 Ctrl+Shift+B 打开命令面板），通过 IPC 通知渲染进程。

桌面通知：Electron 原生 Notification API，支持点击回调（跳转到相关模块）。

开机自启：app.setLoginItemSettings 可配置。

文件操作：Electron 原生 fs 模块（主进程）提供安全的文件读写。

离线优先策略：断网时 — 聊天消息暂存到本地队列（IndexedDB），恢复网络后自动发送；日程数据可从 Redis 缓存查看（只读）；宠物本地正常运行；剪贴板、代码片段等本地模块不受影响。网络恢复时自动同步离线期间的变更。前端顶部状态栏显示网络状态（在线/离线/同步中）。

操作撤销（Undo）：关键删除操作（删除日程、删除知识库文档、删除代码片段）执行后，底部弹出 Ant Design message 提示"已删除"，附带"撤销"按钮，30 秒内可点击撤销恢复（实际为软删除，撤销即恢复 deleted → 0）。超时后由定时任务物理清理。

八、UI 与个性化
8.1 主题系统
主题引擎：Ant Design v6 ConfigProvider + 自定义 Design Token。

暗色模式：Ant Design 暗色算法，一键切换。

主题管理：

内置主题（明亮、暗色、高对比度）。

用户可导入/导出主题 JSON 文件（通过前端上传下载）。

在线主题商店（可选扩展）：从远程仓库下载主题包。

启动恢复：从后端获取当前主题，启动时自动应用。

8.2 前端组件体系
布局：Ant Design Layout（侧边栏 + 头部 + 内容区）。

渐进式加载：核心模块（聊天、设置）随首屏加载，其他模块（日程、剪贴板、代码片段、技能面板等）使用 React.lazy + Suspense 懒加载，首屏加载时间优化。每个懒加载模块包裹 Suspense fallback 显示骨架屏（Ant Design Skeleton）。

聊天面板：List + 自定义 MessageBubble，支持 Markdown 渲染（react-markdown + remark-gfm），代码块语法高亮（prismjs）。

设置面板：Form + Tabs 分区（Ollama 配置、AI 设置、应用设置、宠物设置、快捷键设置、隐私与安全、关于与更新等）。

模块管理：Card + Switch 展示模块列表，Descriptions 展示模块详情。

技能面板：Table 展示技能，支持启用/禁用、炼化、链式配置。

命令面板：Modal + AutoComplete，支持快捷键唤起。

宠物属性面板：Progress + Statistic 实时展示六维属性。

图标：@ant-design/icons v6.0.0。

8.3 自定义 Hooks
useIPC：封装 Zod 类型安全的 IPC 调用。

useTheme：主题切换与持久化。

useAutoScroll：聊天窗口自动滚动到底部。

useDebounce：搜索防抖。

useWebSocket：WebSocket 连接管理、心跳检测（30 秒 ping/pong）与指数退避重连（见 2.3 节）。

九、开发与部署
9.1 开发环境
前端：npm run dev 启动 electron-vite 开发服务器，支持 HMR。

后端：uvicorn main:app --reload 启动 FastAPI，celery -A app.celery worker --loglevel=info 启动任务队列。

数据库：Docker Compose 一键启动 MySQL + Redis + Qdrant（生产环境可单独部署）。

9.2 构建与打包
前端：npm run build 构建生产版本，electron-builder 打包为 .exe / .dmg / .AppImage。

后端：可打包为独立二进制（pyinstaller）或直接部署为 Python 服务。

9.3 部署模式
本地一体模式（默认）：Electron 内嵌后端服务（Electron 启动时自动 spawn Python 进程），适合单机使用。

服务器模式：前端连接到远程后端 API（需配置 Nginx 反向代理），多设备共享数据。

9.4 自动更新
前端：electron-updater 配置更新服务器地址，静默下载并提示用户安装。

后端：通过 Celery 任务拉取更新脚本，热重启服务（需管理员权限）。

附录：完整功能清单
模块	功能	实现技术
工程化	构建、规范、测试、打包、更新、API 版本化、变更日志自动生成	electron-vite, ESLint, Vitest, builder, conventional-commits
日志系统	前后端分级、轮转、聚合、结构化字段（trace_id/user_id）、敏感数据脱敏	electron-log + logging
健康检查	存活/就绪/依赖状态三个端点，配合监控告警	FastAPI
事件总线	模块间通信，错误隔离	Node.js EventEmitter
AI 对话	流式输出、意图路由、工具调用、AI 护栏、语义缓存、用户反馈闭环	Qwen3.5 + LangChain
记忆系统	短期+长期、语义检索、自动摘要	MySQL + Qdrant + Celery
知识库 RAG	多格式导入、混合检索、多跳推理	LlamaIndex + LangChain + LangGraph + Qdrant
翻译模块	术语优先（无资料支持）+ RAG 增强（调 LLM）	Qwen3.5 + RAG
日程提醒	日历视图、定时通知	@ant-design/calendar + Celery
剪贴板历史	监听、搜索、固定	集成成熟 Electron 剪贴板管理方案
代码片段	编辑器、标签、统计	react-codemirror
命令面板	全局快捷键、动态命令	antd AutoComplete + globalShortcut
天气	实时天气、主动问候	open-meteo API
文件预览	文本、代码、图片、PDF	pdf.js + react-codemirror
OCR	截图识别、批量处理	Tesseract.js（纯前端）
3D 宠物	PMX 模型、物理模拟、状态机	Three.js + ammojs
意图学习	用户纠正、隐式反馈	MySQL + Qdrant 向量更新
行为模式检测	LCS 相似度、技能建议	MySQL action_logs + Rust 加速
技能系统	发现、安装、炼化、链式调用	自研 + LangGraph
子代理	复杂任务拆解、并行执行、运行管理面板（一键终止）	LangGraph + Celery
工作流	DAG 编排、定时/事件触发	LangGraph + Celery
视觉模块	屏幕捕获、变化检测、分析	desktopCapturer + llava（可选）
推理深度	CoT/ToT 三档	LangChain 提示词模板
性能监控	资源采集、告警、趋势	psutil + WebSocket
安全	加密、备份、CSP	cryptography + electron
错误处理	前端 ErrorBoundary + 后端全局异常 + WebSocket 恢复	React + FastAPI
主题系统	明亮/暗色、导入导出	Ant Design ConfigProvider
Prompt 管理	版本化存储、回滚、A/B 测试	MySQL prompts 表
离线优先	断网暂存、恢复同步、状态指示	IndexedDB + WebSocket
操作撤销	关键操作 30 秒内可撤销，软删除兜底	Ant Design message
渐进式加载	核心模块首屏加载，其他懒加载 + 骨架屏	React.lazy + Suspense
设置系统	所有配置存 MySQL settings 表，前端读写，WebSocket 同步	Pydantic Settings + MySQL
Beautiful-Elf 是一个功能完整、技术先进、可落地性强的智能桌面助手方案。数据架构采用 MySQL（业务数据）+ Qdrant（向量数据）+ Redis（缓存/消息）三层分离设计，配合 CQRS 读写分离模式，职责清晰、可维护性强。AI 核心采用 LlamaIndex + LangChain + LangGraph + Qdrant + Qwen3.5 构建企业级 RAG 管道，剪贴板和 OCR 等模块直接复用成熟开源方案，设置系统提供从本地模型管理到 AI 参数的精细控制。