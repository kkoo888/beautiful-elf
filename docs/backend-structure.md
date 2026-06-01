# Beautiful-Elf 后端项目结构规范

> 版本：v1.0 | 更新日期：2026-05-30

---

## 📁 目录结构总览

```
beautiful-elf/
│
├── backend/                           # FastAPI 后端
│   ├── main.py                        # 应用入口：FastAPI app 创建、路由注册、中间件、生命周期
│   ├── requirements.txt               # Python 依赖清单
│   ├── alembic.ini                    # Alembic 数据库迁移配置
│   ├── .env / .env.example            # 环境变量
│   ├── .gitignore
│   ├── README.md
│   │
│   ├── alembic/                       # 📦 数据库迁移脚本
│   │   ├── env.py                     # 迁移环境配置
│   │   ├── script.py.mako             # 迁移脚本模板
│   │   └── versions/                  # 迁移版本文件
│   │
│   ├── scripts/                       # 🔧 运维/工具脚本
│   │   └── __init__.py
│   │
│   ├── tests/                         # 🧪 测试
│   │   └── __init__.py
│   │
│   └── app/                           # 🎯 应用核心代码
│       ├── __init__.py
│       │
│       ├── core/                      # 🔧 基础设施层（配置、连接、安全、依赖）
│       │   ├── config.py              # Pydantic Settings — 环境变量统一管理
│       │   ├── database.py            # MySQL 引擎、会话工厂、get_db 依赖
│       │   ├── redis_client.py        # Redis 连接池、get_redis 依赖
│       │   ├── qdrant_client.py       # Qdrant 向量库客户端、get_qdrant 依赖
│       │   ├── security.py            # JWT 令牌签发/校验、bcrypt 密码哈希
│       │   ├── dependencies.py        # 全局 FastAPI 依赖（分页参数、认证校验）
│       │   ├── websocket_manager.py   # WebSocket 连接管理器（按 channel 分组）
│       │   ├── exceptions.py          # 自定义业务异常（AppError 体系）
│       │   └── logging.py             # 日志配置（含 trace_id 链路追踪）
│       │
│       ├── models/                    # 🗄️ SQLAlchemy ORM 模型（按业务域拆分）
│       │   ├── __init__.py            # 统一导出所有模型
│       │   ├── base.py                # 模型基类（id、created_at、updated_at、deleted）
│       │   ├── models.py              # 兼容层（旧 import 不报错，新代码勿用）
│       │   ├── conversation.py        # 会话 & 消息
│       │   ├── memory.py              # 长期记忆
│       │   ├── knowledge.py           # 知识库文档 & 分块
│       │   ├── intent.py              # 意图配置 & 命中统计
│       │   ├── skill.py               # 技能注册 & 使用统计
│       │   ├── workflow.py            # 工作流定义 & 运行记录 & 节点详情
│       │   ├── tool.py                # 工具注册 & 调用统计
│       │   ├── schedule.py            # 日程事件
│       │   ├── clipboard.py           # 剪贴板历史
│       │   ├── snippet.py             # 代码片段 & 标签
│       │   ├── pet.py                 # 宠物属性 & 互动记录
│       │   ├── command.py             # 命令注册 & 使用频率
│       │   ├── performance.py         # 性能采样
│       │   ├── notification.py        # 通知历史
│       │   ├── system.py              # 全局配置 & 助手人格
│       │   ├── backup.py              # 备份记录
│       │   ├── ai_feedback.py         # AI 回答反馈
│       │   ├── prompt.py              # Prompt 版本管理
│       │   ├── action_log.py          # 操作日志
│       │   ├── expert_team.py         # 专家团 & 成员 & 运行记录
│       │   └── llm_provider.py        # 🆕 大模型供应商配置
│       │
│       ├── schemas/                   # 📝 Pydantic 数据模型（API 请求/响应）
│       │   ├── __init__.py
│       │   ├── response.py            # 统一响应格式
│       │   ├── conversation.py        # 会话 schema
│       │   ├── message.py             # 消息 schema
│       │   ├── schedule.py            # 日程 schema
│       │   ├── clipboard.py           # 剪贴板 schema
│       │   ├── snippet.py             # 代码片段 schema
│       │   ├── knowledge.py           # 知识库 schema
│       │   ├── memory.py              # 记忆 schema（待补）
│       │   ├── skill.py               # 技能 schema
│       │   ├── tool.py                # 工具 schema
│       │   ├── workflow.py            # 工作流 schema（待补）
│       │   ├── pet.py                 # 宠物 schema
│       │   ├── command.py             # 命令 schema
│       │   ├── command_usage.py       # 命令使用 schema
│       │   ├── notification.py        # 通知 schema
│       │   ├── performance.py         # 性能 schema
│       │   ├── soul_config.py         # 人格配置 schema
│       │   ├── backup.py              # 备份 schema
│       │   ├── prompt.py              # Prompt schema
│       │   ├── ai_feedback.py         # AI 反馈 schema
│       │   ├── action_log.py          # 操作日志 schema
│       │   ├── config.py              # 配置 schema
│       │   └── llm_provider.py        # 🆕 大模型供应商 schema
│       │
│       ├── services/                  # ⚙️ 业务逻辑层（纯业务编排，不含路由细节）
│       │   ├── __init__.py
│       │   ├── conversation_service.py
│       │   ├── message_service.py
│       │   ├── schedule_service.py
│       │   ├── clipboard_service.py
│       │   ├── snippet_service.py
│       │   ├── skill_service.py
│       │   ├── tool_service.py
│       │   ├── pet_service.py
│       │   ├── command_service.py
│       │   ├── command_usage_service.py
│       │   ├── notification_service.py
│       │   ├── performance_service.py
│       │   ├── config_service.py
│       │   ├── soul_config_service.py
│       │   ├── backup_service.py
│       │   ├── prompt_service.py
│       │   ├── ai_feedback_service.py
│       │   ├── action_log_service.py
│       │   └── llm_provider_service.py  # 🆕 大模型供应商 service
│       │
│       ├── repository/                # 💾 数据访问层（封装数据库 CRUD 操作）
│       │   ├── __init__.py
│       │   ├── conversation_repo.py
│       │   ├── message_repo.py
│       │   ├── schedule_repo.py
│       │   ├── clipboard_repo.py
│       │   ├── snippet_repo.py
│       │   ├── skill_repo.py
│       │   ├── tool_repo.py
│       │   ├── pet_repo.py
│       │   ├── command_repo.py
│       │   ├── command_usage_repo.py
│       │   ├── notification_repo.py
│       │   ├── performance_repo.py
│       │   ├── config_repo.py
│       │   ├── soul_config_repo.py
│       │   ├── backup_repo.py
│       │   ├── prompt_repo.py
│       │   ├── ai_feedback_repo.py
│       │   ├── action_log_repo.py
│       │   └── llm_provider_repo.py     # 🆕 大模型供应商 repo
│       │
│       ├── mappers/                   # 🔄 数据映射器（封装具体存储引擎操作）
│       │   ├── __init__.py
│       │   ├── base.py                # MySQL 通用 CRUD 基类
│       │   ├── redis_mapper.py        # Redis 通用操作（get/set/delete/publish）
│       │   └── qdrant_mapper.py       # Qdrant 向量操作（upsert/search/delete）
│       │
│       ├── api/                       # 🌐 路由层（仅参数校验 + 调用 service）
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── api.py             # ⭐ 路由聚合（统一注册所有 endpoint）
│       │       ├── websocket.py       # WebSocket 端点
│       │       ├── health.py          # 健康检查
│       │       ├── conversation.py    # 会话 CRUD
│       │       ├── message.py         # 消息 CRUD（嵌套路由）
│       │       ├── schedule.py        # 日程 CRUD
│       │       ├── clipboard.py       # 剪贴板 CRUD
│       │       ├── snippet.py         # 代码片段 CRUD
│       │       ├── knowledge.py       # 知识库 CRUD + 语义搜索
│       │       ├── memory.py          # 长期记忆 CRUD + 语义搜索
│       │       ├── skill.py           # 技能 CRUD
│       │       ├── tool.py            # 工具 CRUD
│       │       ├── workflow.py        # 工作流 CRUD + 执行
│       │       ├── pet.py             # 宠物属性管理
│       │       ├── command.py         # 命令管理
│       │       ├── command_usage.py   # 命令使用统计
│       │       ├── notification.py    # 通知管理
│       │       ├── performance.py     # 性能数据
│       │       ├── soul_config.py     # 人格配置
│       │       ├── backup.py          # 备份管理
│       │       ├── prompt.py          # Prompt 管理
│       │       ├── ai_feedback.py     # AI 反馈
│       │       ├── action_log.py      # 操作日志
│       │       ├── config.py          # 配置管理（/{key} 通配放最后）
│       │       └── llm_provider.py    # 🆕 大模型供应商 CRUD
│       │
│       ├── tasks/                     # 📋 Celery 异步任务
│       │   └── __init__.py
│       │
│       └── utils/                     # 🔨 辅助函数
│           └── __init__.py
│
├── shared/                            # 🔗 前后端共享类型
│   └── types/
│       ├── api_contracts.ts           # API 请求/响应类型（与 schemas 同步）
│       └── websocket_messages.ts      # WebSocket 消息类型
│
├── docker-compose.yml                 # 本地开发环境（MySQL, Redis, Qdrant）
├── .gitignore
└── README.md
```

---

## 📐 分层架构

```
┌─────────────────────────────────────────────┐
│                 客户端请求                    │
└──────────────────┬──────────────────────────┘
                   ↓
┌──────────────────┴──────────────────────────┐
│  api/v1/{module}.py    路由层               │
│  - 参数校验（Pydantic schema）              │
│  - 调用 service                              │
│  - 返回统一格式响应                           │
└──────────────────┬──────────────────────────┘
                   ↓
┌──────────────────┴──────────────────────────┐
│  services/{module}_service.py  业务逻辑层    │
│  - 业务编排、事务管理                         │
│  - 调用 repository                           │
│  - 不含 SQL 细节                             │
└──────────────────┬──────────────────────────┘
                   ↓
┌──────────────────┴──────────────────────────┐
│  repository/{module}_repo.py  数据访问层     │
│  - 封装 CRUD 查询                            │
│  - 调用 mapper                               │
│  - 返回 ORM 对象                             │
└──────────────────┬──────────────────────────┘
                   ↓
┌──────────────────┴──────────────────────────┐
│  mappers/  数据映射层                        │
│  - base.py: MySQL 通用 CRUD（SQLAlchemy）    │
│  - redis_mapper.py: Redis 操作封装           │
│  - qdrant_mapper.py: 向量操作封装            │
└──────────────────┬──────────────────────────┘
                   ↓
┌──────────────────┴──────────────────────────┐
│  MySQL / Redis / Qdrant  存储引擎            │
└─────────────────────────────────────────────┘
```

---

## 📋 各目录职责说明

### `core/` — 基础设施层

| 文件 | 职责 | 被谁调用 |
|------|------|---------|
| `config.py` | 环境变量读取（Pydantic Settings） | 所有需要配置的模块 |
| `database.py` | MySQL 引擎、会话工厂、`get_db` 依赖 | repository、api |
| `redis_client.py` | Redis 连接池、`get_redis` 依赖 | service、mappers |
| `qdrant_client.py` | Qdrant 客户端、`get_qdrant` 依赖 | service、mappers |
| `security.py` | JWT 签发/校验、密码哈希 | dependencies、api |
| `dependencies.py` | 分页参数、认证校验等全局依赖 | api |
| `websocket_manager.py` | WS 连接管理（按 channel 分组） | api、service |
| `exceptions.py` | 自定义业务异常体系 | service、api |
| `logging.py` | 日志配置 + trace_id 链路追踪 | 所有模块 |

### `models/` — ORM 模型层

| 规则 | 说明 |
|------|------|
| **按业务域拆分** | 每个域一个文件，不堆在单文件 |
| **统一导出** | `__init__.py` 导出所有模型 |
| **兼容层** | `models.py` 保留旧 import 路径，新代码勿用 |
| **基类** | `base.py` 提供 id、created_at、updated_at、deleted 软删除 |

### `schemas/` — 数据校验层

| 规则 | 说明 |
|------|------|
| **与 models 一一对应** | 每个模型有对应的 schema 文件 |
| **请求/响应分离** | 同一文件内定义 Create/Update/Response |
| **统一响应** | `response.py` 定义标准响应格式 |

### `services/` — 业务逻辑层

| 规则 | 说明 |
|------|------|
| **纯业务编排** | 不含 SQL、不含路由、不含 HTTP 细节 |
| **事务管理** | 通过 `db: AsyncSession` 控制事务 |
| **可组合** | service 可调用其他 service |

### `repository/` — 数据访问层

| 规则 | 说明 |
|------|------|
| **封装 CRUD** | 通过 `MySQLMapper` 基类统一操作 |
| **返回 ORM 对象** | 不做序列化，schema 层处理 |
| **不含业务逻辑** | 只做查询拼装 |

### `mappers/` — 数据映射层

| 文件 | 职责 |
|------|------|
| `base.py` | MySQL 通用 CRUD（find_by_id、create、update、soft_delete） |
| `redis_mapper.py` | Redis 通用操作（get/set/delete/publish/expire） |
| `qdrant_mapper.py` | 向量操作（upsert/search/delete/collection 管理） |

### `api/v1/` — 路由层

| 文件 | 职责 |
|------|------|
| `api.py` | ⭐ 路由聚合，统一注册所有 endpoint |
| `websocket.py` | WebSocket 端点 `/ws/{channel}` |
| `health.py` | 健康检查 `/health` |
| 其他 `*.py` | 各业务路由，**仅做参数校验 + 调用 service** |

### `tasks/` — 异步任务层

| 规则 | 说明 |
|------|------|
| **Celery 任务** | 耗时操作异步处理（文件解析、向量化等） |
| **按业务拆分** | 每个域一个 task 文件 |

---

## 🔌 新增功能 Checklist

### 新增业务模块（完整链路）

- [ ] **model**: `models/{domain}.py` — 创建 ORM 模型
- [ ] **schema**: `schemas/{domain}.py` — 创建 Pydantic schema（Create/Update/Response）
- [ ] **mapper**: 如需新的存储引擎操作，在 `mappers/` 中添加
- [ ] **repository**: `repository/{domain}_repo.py` — 创建数据访问层
- [ ] **service**: `services/{domain}_service.py` — 创建业务逻辑层
- [ ] **api**: `api/v1/{domain}.py` — 创建路由
- [ ] **注册路由**: 在 `api/v1/api.py` 中 `include_router`
- [ ] **迁移**: `alembic revision --autogenerate` 生成数据库迁移

### 新增 API 端点

- [ ] 在 `api/v1/{module}.py` 中添加路由函数
- [ ] 在 `schemas/{module}.py` 中添加请求/响应 schema
- [ ] 路由函数**仅做参数校验 + 调用 service**，不含业务逻辑

### 新增 WebSocket channel

- [ ] 客户端连接 `ws://host/api/v1/ws/{channel}`
- [ ] 服务端通过 `ws_manager.broadcast(channel, data)` 推送
- [ ] channel 命名规范：`chat`、`pet`、`notification`、`system`

### 新增全局依赖

- [ ] 在 `core/dependencies.py` 中添加
- [ ] 通过 `Depends()` 注入到路由

---

## 🚫 常见错误

| 错误做法 | 正确做法 |
|---------|---------|
| API 端点硬编码在路由文件 | 在路由文件中只做校验 + 调用 service |
| service 里写 SQL | SQL 操作放 repository，service 只编排 |
| repository 里写业务逻辑 | 业务逻辑放 service，repository 只 CRUD |
| models 全堆一个文件 | 按业务域拆分到独立文件 |
| 直接操作 Redis/Qdrant | 通过 mapper 封装 |
| 路由函数返回格式不统一 | 使用 `response.py` 统一格式 |
| 新模块不注册路由 | 必须在 `api/v1/api.py` 中 include_router |
| WebSocket 连接手动管理 | 使用 `ws_manager` 全局管理 |
| 密码明文存储 | 通过 `security.py` bcrypt 哈希 |
| 无认证保护的接口 | 使用 `Depends(require_auth)` 强制认证 |

---

## 🏗️ 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 异步、自动文档、类型校验 |
| ORM | SQLAlchemy 2.0 (async) | 异步数据库操作 |
| 数据库 | MySQL (aiomysql) | 主数据存储 |
| 数据库迁移 | Alembic | 版本化迁移脚本 |
| 缓存 | Redis (redis-py) | 缓存、会话、消息队列 |
| 向量数据库 | Qdrant | 语义搜索、知识库向量化 |
| 任务队列 | Celery | 异步任务处理 |
| 认证 | JWT (PyJWT) + bcrypt | 令牌认证 + 密码哈希 |
| 数据校验 | Pydantic v2 | 请求/响应 schema |
| WebSocket | FastAPI WebSocket | 实时通信 |
| 日志 | Python logging + trace_id | 链路追踪 |
