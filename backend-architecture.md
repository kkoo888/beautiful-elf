# Beautiful-Elf 后端架构关系图

## 🏗️ 整体分层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        前端 (Electron)                               │
│              HTTP 请求 / WebSocket 长连接 / 通知接收                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI 路由层 (API Layer)                        │
│                                                                     │
│  路径风格: 复数名词 snake_case (如 /api/v1/pet_attributes)           │
│                                                                     │
│  /api/v1/ai/*               /api/v1/schedules/*                     │
│  /api/v1/memory-entries/*   /api/v1/clipboard-items/*               │
│  /api/v1/snippets/*         /api/v1/knowledge-documents/*           │
│  /api/v1/skills/*           /api/v1/workflows/*                     │
│  /api/v1/pet-attributes/*   /api/v1/config/*                        │
│  /api/v1/health/*           /api/v1/ws (WebSocket)                  │
│                                                                     │
│  职责: 路由分发、请求校验 (Pydantic)、认证、错误码映射                │
│  不含业务逻辑，仅调用 Service 层                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Service 层 (CQRS 读写分离)                         │
│                                                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────────────┐  │
│  │    CommandService        │  │    QueryService                  │  │
│  │    (写操作)              │  │    (读操作)                       │  │
│  │                         │  │                                  │  │
│  │  - 创建/更新/删除数据    │  │  - 查询展示数据                   │  │
│  │  - 严格校验 (Pydantic)  │  │  - 可走 Redis 缓存               │  │
│  │  - 写入后触发事件:      │  │  - 只读连接 / 聚合多数据源        │  │
│  │    · 缓存失效           │  │  - 独立优化，不影响写入            │  │
│  │    · 向量同步           │  │                                  │  │
│  │    · WebSocket 广播     │  │                                  │  │
│  │    · 通知推送           │  │                                  │  │
│  └────────────┬────────────┘  └──────────────┬───────────────────┘  │
│               │                              │                      │
│               ▼                              ▼                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Repository 层                              │   │
│  │                                                              │   │
│  │  ScheduleRepository    MemoryRepository    PetRepository     │   │
│  │  ChatRepository        KnowledgeRepository SkillRepository   │   │
│  │  ConfigRepository      WorkflowRepository  ...               │   │
│  │                                                              │   │
│  │  职责: 业务数据的 CRUD 操作编排，不直接操作存储引擎             │   │
│  │  调用 Data Mapper 完成具体读写                                │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Data Mapper / DAO 层 (数据映射)                      │
│                                                                     │
│  封装对 MySQL / Redis / Qdrant 的具体操作，上层无需感知底层驱动       │
│                                                                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐  │
│  │  MySQL Mapper     │ │  Redis Mapper     │ │  Qdrant Mapper      │  │
│  │                  │ │                  │ │                    │  │
│  │  SQLAlchemy ORM  │ │  aioredis 封装   │ │  qdrant-client 封装 │  │
│  │  + Alembic 迁移  │ │                  │ │                    │  │
│  │                  │ │  get() / set()   │ │  upsert()          │  │
│  │  find_by_id()    │ │  delete()        │ │  search()          │  │
│  │  find_all()      │ │  exists()        │ │  delete_by_filter() │  │
│  │  create()        │ │  expire()        │ │  get_by_id()        │  │
│  │  update()        │ │  publish()       │ │  count()            │  │
│  │  soft_delete()   │ │  subscribe()     │ │                    │  │
│  │  bulk_insert()   │ │                  │ │  向量操作全部封装    │  │
│  │                  │ │                  │ │                    │  │
│  │  连接池管理:      │ │  连接池管理:      │ │  连接管理:           │  │
│  │  pool_size=10    │ │  max_conn=20     │ │  集合生命周期        │  │
│  │  max_overflow=20 │ │                  │ │                    │  │
│  └──────────────────┘ └──────────────────┘ └────────────────────┘  │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         存储层 (Storage)                              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  MySQL 9.5    │  │  Redis 8.6    │  │  Qdrant                   │  │
│  │              │  │              │  │                          │  │
│  │  业务数据     │  │  缓存         │  │  AI 向量数据              │  │
│  │  唯一真相源   │  │  消息代理      │  │                          │  │
│  │              │  │              │  │  intent_vectors          │  │
│  │  所有 CRUD   │  │  热数据缓存    │  │  knowledge_chunks        │  │
│  │  业务数据     │  │  Celery Broker │  │  memory_vectors          │  │
│  │              │  │  WebSocket 队列│  │                          │  │
│  │  Alembic     │  │              │  │  通过 ID 关联 MySQL      │  │
│  │  Schema 管理  │  │              │  │  可从 MySQL 重建         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ⚠️ 连接信息通过环境变量/命令行参数传入，不存 MySQL                    │
│  ✅ 业务配置 (AI 参数、模型选择、功能开关) 存 MySQL settings 表        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🌐 CORS 配置

> 本地模式下 Electron 渲染进程 (file:// 或 localhost:5173) 请求 FastAPI (localhost:8000)，必须配置 CORS。

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # electron-vite 开发服务器
        "file://",                  # Electron 打包后
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],  # 前端需要读取 trace_id
)
```

**安全约束**:
- [强制] 生产环境禁止 `allow_origins=["*"]`
- [强制] 仅允许 Electron 应用自身的源
- [推荐] 服务器模式下通过 Nginx 配置 CORS，不在应用层处理

---

## 🔄 后端主动推送架构（事件驱动）

> 日程、告警、工作流等定时/异步任务由后端触发，主动推送给前端。

```
┌─────────────────────────────────────────────────────────────────────┐
│                     后端主动推送机制                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Celery Beat (定时调度器)                                     │   │
│  │                                                              │   │
│  │  每分钟扫描:                                                  │   │
│  │    ├── 日程提醒 (schedules 表, 提前提醒时间匹配)               │   │
│  │    ├── 宠物属性衰减 (pet_attributes 表, 每小时)               │   │
│  │    └── 过期数据清理 (action_logs 7天TTL, 软删除物理清理)      │   │
│  │                                                              │   │
│  │  每5分钟:                                                     │   │
│  │    └── 性能采样清理 (performance_metrics 保留最新 360 条)      │   │
│  │                                                              │   │
│  │  每3天凌晨:                                                   │   │
│  │    └── MySQL 备份 (mysqldump)                                 │   │
│  │                                                              │   │
│  │  每日:                                                        │   │
│  │    └── 对话摘要生成 (messages → memory_entries)               │   │
│  └─────────────────────┬───────────────────────────────────────┘   │
│                        │                                            │
│  ┌─────────────────────▼───────────────────────────────────────┐   │
│  │  Celery Worker (异步任务执行)                                 │   │
│  │                                                              │   │
│  │  任务队列:                                                    │   │
│  │    ├── 知识库文档 embedding (LlamaIndex + Qwen3-Embedding)   │   │
│  │    ├── 意图向量更新 (重新 embedding)                          │   │
│  │    ├── 工作流执行 (LangGraph StateGraph)                     │   │
│  │    ├── 子代理调度 (LangGraph 多代理)                         │   │
│  │    ├── 数据同步 (MySQL → Qdrant 向量同步)                    │   │
│  │    └── 备份任务                                               │   │
│  └─────────────────────┬───────────────────────────────────────┘   │
│                        │                                            │
│                        │ 任务完成/状态变更                            │
│                        ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  WebSocket 事件推送 (FastAPI WebSocket)                       │   │
│  │                                                              │   │
│  │  连接鉴权:                                                    │   │
│  │    客户端连接时携带 token 查询参数                             │   │
│  │    ws://localhost:8000/api/v1/ws?token=<jwt_token>           │   │
│  │    服务端验证 JWT (PyJWT)，失败返回 403 关闭连接              │   │
│  │    token 过期后客户端需重新获取再重连                          │   │
│  │                                                              │   │
│  │  事件类型:                                                    │   │
│  │    ├── schedule_reminder    → 日程提醒弹窗                    │   │
│  │    ├── workflow_progress    → 工作流执行进度                   │   │
│  │    ├── workflow_complete    → 工作流完成通知                   │   │
│  │    ├── subagent_status     → 子代理状态变更                   │   │
│  │    ├── pet_state_update    → 宠物属性变更                     │   │
│  │    ├── config_update       → 配置变更广播                     │   │
│  │    ├── performance_alert   → 性能告警 (CPU>80% 等)            │   │
│  │    ├── skill_suggestion    → 技能建议                        │   │
│  │    └── notification        → 通用通知                        │   │
│  │                                                              │   │
│  │  消息格式:                                                    │   │
│  │  {                                                           │   │
│  │    "type": "事件类型",                                        │   │
│  │    "payload": { ... },                                       │   │
│  │    "timestamp": 1234567890,                                  │   │
│  │    "event_id": "uuid"                                        │   │
│  │  }                                                           │   │
│  │                                                              │   │
│  │  event_id 用于前端去重 (断线重连时避免重复处理)                 │   │
│  └─────────────────────┬───────────────────────────────────────┘   │
│                        │                                            │
│                        ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  前端接收                                                    │   │
│  │    ├── Ant Design Notification 弹窗 (即时提醒)               │   │
│  │    ├── 通知面板历史列表 (持久化)                              │   │
│  │    ├── Zustand 状态更新 (宠物/性能等实时数据)                 │   │
│  │    └── TanStack Query 缓存失效 (数据变更)                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏥 健康检查端点

| 端点 | 用途 | 检查内容 |
|------|------|---------|
| `GET /api/v1/health` | 存活检查 | 进程是否存活，始终返回 200 |
| `GET /api/v1/ready` | 就绪检查 | 所有依赖是否可用，任一不可用返回 503 |
| `GET /api/v1/deps` | 依赖详情 | 各依赖详细状态，供运维排查 |

### /health — 存活检查

```json
// GET /api/v1/health → 200
{ "status": "alive", "timestamp": 1716825600 }
```

### /ready — 就绪检查

```json
// GET /api/v1/ready → 200 (全部就绪) 或 503 (任一不可用)
{
  "status": "ready",
  "checks": {
    "mysql":  { "status": "ok", "latency_ms": 2 },
    "redis":  { "status": "ok", "latency_ms": 1 },
    "qdrant": { "status": "ok", "latency_ms": 5 },
    "ollama": { "status": "ok", "latency_ms": 10 }
  }
}
```

### /deps — 依赖详情

```json
// GET /api/v1/deps → 200
{
  "mysql":  { "version": "9.5.0", "pool_size": 10, "pool_used": 3, "latency_ms": 2 },
  "redis":  { "version": "8.6.0", "pool_size": 20, "pool_used": 5, "latency_ms": 1 },
  "qdrant": { "version": "1.x", "collections": 3, "latency_ms": 5 },
  "ollama": { "models": ["qwen3.5:7b", "qwen3-embedding:latest"], "latency_ms": 10 }
}
```

**告警阈值**:
- 连接池使用率 > 80% → 日志告警
- 依赖延迟 > 500ms → 日志告警
- Ollama 不可用 → 标记降级（跳过语义缓存，意图识别使用规则匹配 fallback）

---

## 🚦 请求限制

> 去掉 API 限流，但保留基本的请求大小和超时限制。

| 限制项 | 值 | 说明 |
|--------|-----|------|
| 请求体大小 | 10MB | FastAPI 默认，知识库上传文件最大 10MB |
| 文件上传大小 | 50MB | 知识库文档单独限制 |
| 接口超时 | 30s | 普通 API 超时 |
| AI 对话超时 | 120s | Ollama 推理可能较慢 |
| 工作流执行超时 | 300s | 复杂工作流需要更长时间 |
| WebSocket 消息大小 | 1MB | 单条 WebSocket 消息上限 |

```python
# FastAPI 请求体大小限制 (通过 middleware)
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# 文件上传单独限制
@router.post("/api/v1/knowledge/upload")
async def upload_document(
    file: UploadFile = File(..., max_length=50 * 1024 * 1024)  # 50MB
):
    ...
```

---

## 📌 API 版本废弃策略

| 阶段 | 时间 | 行为 |
|------|------|------|
| 当前版本 | - | `/api/v1/*` 正常使用 |
| 新版本发布 | - | `/api/v2/*` 上线，v1 继续运行 |
| 废弃通知 | v2 发布后 30 天 | v1 响应头添加 `Deprecation: true` + `Sunset: <日期>` |
| 废弃警告 | 废弃前 14 天 | v1 响应头添加 `Warning: 299 - "API v1 将于 XX 日下线"` |
| 下线 | 废弃日期 | v1 返回 410 Gone，提示升级 |

```
# 废弃响应头示例
HTTP/1.1 200 OK
Deprecation: true
Sunset: 2026-08-01T00:00:00Z
Link: </api/v2/schedules>; rel="successor-version"
```

---

## 📊 核心模块后端关系

### 💬 AI 对话 & 意图识别

```
用户输入文本
  │
  ▼
FastAPI /api/v1/ai/chat
  │
  ├──→ QueryService → Redis Mapper → Redis
  │      语义缓存查询 (embedding 相似度 < 0.05 → 返回缓存回答)
  │
  ├──→ Qdrant Mapper → Qdrant
  │      intent_vectors Collection 相似度搜索
  │      返回 top-1 { intent_id, score }
  │
  ├──→ MySQL Mapper → MySQL
  │      intents 表查询完整配置 (用 intent_id)
  │
  ├──→ [命中意图] → 路由到对应模块工具
  │      intent_usage 统计更新 (仅记录日志，不限流)
  │
  └──→ [未命中] → 通用对话
         │
         ├──→ Qdrant Mapper → Qdrant
         │      knowledge_chunks + memory_vectors 联合检索
         │
         ├──→ MySQL Mapper → MySQL
         │      knowledge_documents / memory_entries 回查完整数据
         │
         ├──→ Ollama (Qwen3.5)
         │      RAG 增强生成回答
         │
         └──→ CommandService
                messages 表写入对话记录
                WebSocket 流式推送回答
```

### 📅 日程提醒（后端定时驱动）

```
┌──────────────────────────────────────────────────────────┐
│  Celery Beat (每分钟扫描)                                 │
│                                                          │
│  MySQL Mapper → MySQL                                    │
│    SELECT id, title, description, start_time,            │
│           reminder_minutes                               │
│    FROM schedules                                        │
│    WHERE reminded = 0                                    │
│    AND deleted = 0                                       │
│    AND DATE_SUB(start_time,                              │
│        INTERVAL reminder_minutes MINUTE) <= NOW()        │
│                                                          │
│  匹配到日程 →                                             │
│    ├── CommandService → MySQL Mapper                     │
│    │     schedules.reminded = 1                          │
│    │                                                    │
│    └── WebSocket Push                                    │
│          type: "schedule_reminder"                       │
│          payload: { id, title, time, description }       │
│          ↓                                               │
│          前端: Electron Notification 弹窗                 │
│               + 通知面板写入历史                           │
└──────────────────────────────────────────────────────────┘
```

### 📚 知识库 RAG 管道

```
文档导入 (PDF/DOCX/MD/TXT/JSON/CSV/YAML/HTML/XML/ZIP)
  │
  ▼
CommandService
  │
  ├──→ Celery 任务 (异步)
  │      │
  │      ├── LlamaIndex SimpleDirectoryReader 加载文档
  │      ├── SemanticSplitterNodeParser 语义分块
  │      │     (失败降级 → RecursiveCharacterTextSplitter)
  │      ├── Qwen3-Embedding 向量化每个块
  │      │
  │      ├── Qdrant Mapper → Qdrant
  │      │     upsert knowledge_chunks Collection
  │      │     payload: { doc_id, chunk_index }
  │      │
  │      └── MySQL Mapper → MySQL
  │            knowledge_documents 表写入元数据
  │            knowledge_chunks 表记录向量 ID 映射
  │
  ▼
检索 & 生成
  │
  ├── Qdrant Mapper → Qdrant
  │     混合检索: 向量 (0.7) + 关键字全文 (0.3)
  │
  ├── MySQL Mapper → MySQL
  │     knowledge_documents 回查完整数据
  │
  ├── [可选] CrossEncoder 重排序
  │
  ├── LangGraph 多跳推理
  │     复杂问题 → 拆解为多步检索
  │
  └── Ollama (Qwen3.5)
        流式回答 + 来源引用
```

### 🔧 技能系统

```
技能发现: 扫描 skills/ 目录 SKILL.md (YAML Front Matter)
  │
  ▼
CommandService
  │
  ├──→ MySQL Mapper → MySQL
  │     skills 表注册元数据 + 启用状态
  │
  ├──→ 意图路由关联
  │     Qdrant Mapper → Qdrant
  │       intent_vectors 更新触发词向量
  │     MySQL Mapper → MySQL
  │       intents 表更新目标模块
  │
  └──→ 技能炼化
        MySQL Mapper → MySQL
          skill_stats 表读取统计数据 (调用次数、成功率、平均耗时)
          仅用于日志展示和优化建议，不限流
        Ollama (Qwen3.5)
          分析并生成优化建议
```

### 🐾 宠物状态系统

```
┌──────────────────────────────────────────────────────────┐
│  宠物属性衰减 (Celery Beat 每小时)                         │
│                                                          │
│  MySQL Mapper → MySQL                                    │
│    UPDATE pet_attributes                                 │
│    SET hunger = GREATEST(hunger - 5, 10),                │
│        clean  = GREATEST(clean - 3, 10),                 │
│        mood   = GREATEST(mood - 2, 10)                   │
│    WHERE ...                                             │
│                                                          │
│  属性变化 → WebSocket Push                                │
│    type: "pet_state_update"                              │
│    payload: { hunger, clean, mood, health, intimacy, lv }│
│                                                          │
│  低属性触发:                                               │
│    hunger < 30 → 饥饿动画 + 气泡 "我好饿..."              │
│    clean < 40  → 脏动画                                  │
│    mood < 20   → 郁闷动画                                │
└──────────────────────────────────────────────────────────┘

用户互动 (喂食/清洁/聊天)
  │
  ▼
CommandService
  ├──→ MySQL Mapper → MySQL
  │     pet_attributes 更新属性值
  │     pet_interactions 记录互动日志
  │
  └──→ WebSocket Push → 宠物窗口触发动画 + 属性面板更新

离线结算 (宠物窗口重开)
  │
  ▼
QueryService
  ├──→ MySQL Mapper → MySQL
  │     pet_attributes.last_active_at 读取
  │     计算离线时长 → 一次性衰减
  │
  └──→ CommandService → MySQL Mapper
        更新属性 (不低于 10%)
```

### ⚙️ 配置管理

```
┌──────────────────────────────────────────────────────────┐
│  MySQL settings 表 (KV 结构)                              │
│                                                          │
│  ✅ 存 MySQL 的业务配置:                                   │
│    - AI 参数 (temperature, max_tokens, top_p)             │
│    - 模型选择 (对话/嵌入/视觉模型名称)                      │
│    - Ollama 服务地址                                      │
│    - 功能开关 (行为模式检测、语义缓存等)                    │
│    - 宠物设置 (衰减速度、气泡频率)                         │
│    - 快捷键映射                                           │
│    - 主题配置                                             │
│    - Prompt 版本 (prompts 表)                             │
│    - restart_required 标记                                │
│                                                          │
│  ⚠️ 不存 MySQL 的连接配置:                                 │
│    - MySQL 连接地址/密码 → 环境变量                        │
│    - Redis 连接地址/密码 → 环境变量                        │
│    - Qdrant 连接地址 → 环境变量                            │
│    (因为这些是存储引擎自身的依赖，不能从 MySQL 读取)         │
│                                                          │
│  配置加载流:                                               │
│    启动 → 从 MySQL 加载全部配置到内存                       │
│    运行 → 直接读取内存配置 (零延迟)                         │
│    修改 → API /api/v1/config                              │
│           → 更新 MySQL settings 表                        │
│           → 刷新内存配置                                   │
│           → WebSocket 广播 config_update                   │
│           → 热更新即时生效 / 需重启弹窗提示                 │
└──────────────────────────────────────────────────────────┘
```

---

## 🔌 Data Mapper / DAO 层详细设计

> 上层 (Repository / Service) 不直接接触 aiomysql、aioredis、qdrant-client，全部通过 Mapper 封装。

### MySQL Mapper

```python
class MySQLMapper:
    """封装 SQLAlchemy ORM 操作"""

    # 连接池 (启动时初始化)
    # pool_size=10, max_overflow=20, pool_timeout=30, pool_recycle=3600

    async def find_by_id(self, model: Type[T], id: int) -> Optional[T]
    async def find_all(self, model: Type[T], filters: dict, 
                       offset: int, limit: int) -> List[T]
    async def create(self, model: Type[T], data: dict) -> T
    async def update(self, model: Type[T], id: int, data: dict) -> T
    async def soft_delete(self, model: Type[T], id: int) -> None
        # deleted = 0 → 1
    async def bulk_insert(self, model: Type[T], items: List[dict]) -> None
    async def execute_raw(self, sql: str, params: dict) -> Any
        # 仅用于复杂查询，慎用
```

### Redis Mapper

```python
class RedisMapper:
    """封装 aioredis 操作"""

    # 连接池 (启动时初始化)
    # max_connections=20

    # 缓存操作
    async def get(self, key: str) -> Optional[str]
    async def set(self, key: str, value: str, ttl: int = None) -> None
    async def delete(self, key: str) -> None
    async def exists(self, key: str) -> bool
    async def expire(self, key: str, ttl: int) -> None

    # 发布/订阅 (WebSocket 消息队列)
    async def publish(self, channel: str, message: str) -> None
    async def subscribe(self, channel: str) -> AsyncIterator[str]
```

### Qdrant Mapper

```python
class QdrantMapper:
    """封装 qdrant-client 操作"""

    # 集合管理
    async def ensure_collection(self, name: str, vector_size: int) -> None
    async def delete_collection(self, name: str) -> None

    # 向量操作
    async def upsert(self, collection: str, id: str, 
                     vector: List[float], payload: dict) -> None
    async def search(self, collection: str, query_vector: List[float],
                     limit: int, score_threshold: float,
                     filter_payload: dict = None) -> List[SearchResult]
    async def get_by_id(self, collection: str, id: str) -> Optional[Record]
    async def delete_by_filter(self, collection: str, 
                               filter_payload: dict) -> None
    async def count(self, collection: str, filter_payload: dict = None) -> int

    # 批量操作 (Rust 加速)
    async def batch_search(self, collection: str, 
                           query_vectors: List[List[float]],
                           limit: int) -> List[List[SearchResult]]
```

---

## 🛡️ 异常处理分层

> 每层有明确的异常处理职责，禁止在业务代码中 catch 大范围 Exception。

```
┌─ Mapper 层 ──────────────────────────────────────────────────────┐
│  捕获底层驱动异常 (aiomysql / aioredis / qdrant-client)            │
│  → 包装为统一的 StorageError                                       │
│  → 上层不感知具体驱动                                              │
│  示例:                                                             │
│    MySQLMapper.create() → catch IntegrityError → StorageError      │
│    RedisMapper.get() → catch ConnectionError → StorageError        │
│    QdrantMapper.search() → catch UnexpectedResponse → StorageError │
└──────────────────────────────────────────────────────────────────┘

┌─ Repository 层 ──────────────────────────────────────────────────┐
│  捕获 StorageError → 转换为业务异常 (BusinessError)                 │
│  示例:                                                             │
│    RecordNotFoundError    → 查询不到记录                           │
│    DuplicateEntryError    → 唯一约束冲突                           │
│    DataConsistencyError   → 数据一致性问题                         │
└──────────────────────────────────────────────────────────────────┘

┌─ Service 层 ─────────────────────────────────────────────────────┐
│  捕获 BusinessError → 决定是否重试 / 降级 / 直接抛出                │
│  写操作失败 → 记录修复队列 (Celery)                                │
│  读操作失败 → 尝试降级 (如 MySQL 不可用 → 读 Redis 缓存)           │
└──────────────────────────────────────────────────────────────────┘

┌─ 路由层 ────────────────────────────────────────────────────────┐
│  注册全局 exception_handler                                       │
│  捕获所有未处理异常 → 标准错误格式返回                              │
│  { "code": "MODULE_ERROR_TYPE", "message": "...",                 │
│    "request_id": "trace_id" }                                     │
│  trace_id 在请求入口生成，全链路透传                                │
└──────────────────────────────────────────────────────────────────┘
```

**异常类定义**:

```python
# 基础异常
class AppError(Exception):
    """应用异常基类"""
    code: str
    message: str
    status_code: int

# Mapper 层异常
class StorageError(AppError):
    """存储层通用异常"""
    code = "SYSTEM_STORAGE_ERROR"
    status_code = 500

# Repository 层异常
class RecordNotFoundError(AppError):
    code = "SYSTEM_NOT_FOUND"
    status_code = 404

class DuplicateEntryError(AppError):
    code = "SYSTEM_DUPLICATE"
    status_code = 409

class DataConsistencyError(AppError):
    code = "SYSTEM_CONSISTENCY"
    status_code = 500

# 业务异常 (按模块前缀)
class IntentNotFoundError(AppError):
    code = "INTENT_NOT_FOUND"
    status_code = 404

class OllamaTimeoutError(AppError):
    code = "OLLAMA_TIMEOUT"
    status_code = 503

class RagIndexError(AppError):
    code = "RAG_INDEX_ERROR"
    status_code = 500

# Pydantic 校验失败统一格式
# FastAPI 自动处理 422，自定义格式:
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "code": "SYSTEM_VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "request_id": request.state.trace_id,
            "details": [
                {
                    "field": ".".join(str(loc) for loc in e["loc"]),
                    "message": e["msg"],
                    "type": e["type"]
                }
                for e in exc.errors()
            ]
        }
    )
```

---

## 📝 日志规约

> 遵循 P3C 规范，结构化日志，敏感数据脱敏。

| 规则 | 级别 | 说明 |
|------|------|------|
| 所有日志必须携带 trace_id | [强制] | 请求链路 ID，跨 API → Celery → Qdrant 全链路透传 |
| 敏感数据自动脱敏 | [强制] | API Key/Token/密码/用户消息内容，保留前后几位，中间用 *** |
| 使用占位符而非拼接 | [强制] | ✅ `logger.info("用户 {} 登录", uid)` ❌ `"用户" + uid + "登录"` |
| 禁止 print 输出日志 | [强制] | 统一使用 Python logging |
| 分级输出 | [推荐] | DEBUG(开发) / INFO(正常) / WARN(告警) / ERROR(故障) |
| 日志轮转 | [推荐] | 单文件 10MB，最多 5 个归档 |
| 按模块分文件 | [推荐] | chat.log / pet.log / schedule.log / rag.log |

**结构化日志字段**:

```json
{
  "timestamp": "2026-05-26T23:49:00+08:00",
  "level": "INFO",
  "module": "schedule",
  "trace_id": "abc-123-def",
  "user_id": "1",
  "message": "日程提醒推送成功",
  "extra": { "schedule_id": 42, "title": "***" }
}
```

---

## 🔒 安全规约

| 规则 | 级别 | 实现方式 |
|------|------|---------|
| SQL 参数化 | [强制] | SQLAlchemy ORM / 参数化查询，禁止字符串拼接 |
| 用户输入校验 | [强制] | Pydantic 模型校验所有请求参数 |
| 敏感配置加密 | [强制] | API Key 等加密存储，不落日志 |
| WebSocket 鉴权 | [强制] | JWT token 验证，连接时通过查询参数传递 |
| CORS 限制 | [强制] | 仅允许 Electron 应用自身的源，禁止 `*` |
| 文件上传限制 | [强制] | 限制类型 + 大小 + 二次校验内容 |
| 请求大小限制 | [强制] | 普通 API 10MB，文件上传 50MB |
| 接口超时 | [强制] | 普通 30s / AI 对话 120s / 工作流 300s |
| 密钥轮换 | [推荐] | 定期轮换密钥 |
| 审计日志 | [推荐] | 关键操作保留审计轨迹 |

---

## 📐 命名规约

### Python (后端)

| 类型 | 规则 | 示例 |
|------|------|------|
| 文件名 | snake_case | `schedule_service.py` |
| 类名 | PascalCase | `ScheduleService` |
| 函数/变量 | snake_case | `get_schedule_by_id` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 私有方法 | _leading_underscore | `_internal_method` |
| 异常类 | PascalCase + Error 后缀 | `RecordNotFoundError` |

### 数据库

| 类型 | 规则 | 示例 |
|------|------|------|
| 表名 | snake_case 复数 | `schedules`, `pet_attributes` |
| 字段名 | snake_case | `created_at`, `reminder_time` |
| 主键 | id (BIGINT UNSIGNED) | `id` |
| 外键 | 表名单数_id | `conversation_id`, `workflow_id` |
| 索引 | idx_table_field | `idx_messages_conversation_id` |
| 唯一索引 | uk_table_field | `uk_settings_key` |
| 字符集 | UTF-8MB4 | 全库统一 |

### API

| 类型 | 规则 | 示例 |
|------|------|------|
| 路径 | 复数名词 snake_case | `/api/v1/pet_attributes` |
| 路径版本 | /api/v{N}/ | `/api/v1/schedules` |
| 错误码 | MODULE_ERROR_TYPE | `INTENT_NOT_FOUND` |
| 事件类型 | snake_case | `schedule_reminder` |
| 响应字段 | snake_case | `{ "created_at": "..." }` |

---

## 🧪 工程规约

| 规则 | 级别 | 说明 |
|------|------|------|
| 核心 Service 必须有单测 | [强制] | 覆盖 CommandService / QueryService |
| 测试命名 | [推荐] | `test_<模块>_<场景>_<预期结果>` |
| 提交触发 lint + test | [推荐] | Husky + lint-staged (已有) |
| main 分支保护 | [推荐] | PR 必须 review + CI 通过 |

---

## 📦 技术栈对照表

| 层级 | 技术 | 版本 | 职责 |
|------|------|------|------|
| **路由层** | FastAPI + Uvicorn | 0.124 + 0.47 | HTTP API + WebSocket |
| **数据校验** | Pydantic | 2.12.5 | 请求/响应校验 |
| **Service 层** | 自研 CQRS | - | 读写分离、业务编排 |
| **Repository 层** | 自研 | - | 业务数据 CRUD 编排 |
| **Data Mapper** | SQLAlchemy + aioredis + qdrant-client | 2.0.46 / - | 存储操作封装 |
| **迁移** | Alembic | 1.18.1 | MySQL Schema 版本化 |
| **任务队列** | Celery + Redis Broker | 5.6 + 8.6 | 异步任务 + 定时调度 |
| **AI 编排** | LlamaIndex + LangChain + LangGraph | 最新 | RAG + 工具调用 + 多代理 |
| **本地模型** | Ollama (Qwen3.5 + Qwen3-Embedding) | 最新 | 对话 + 嵌入 |
| **向量数据库** | Qdrant | 最新 | AI 向量检索 |
| **高性能计算** | Rust + PyO3 + maturin | 最新 | 批量向量相似度、pHash、LCS |
| **反向代理** | Nginx (可选) | 1.30 | 服务器部署模式 |
| **代码规范** | Ruff | 0.9 | Python 代码检查 |
