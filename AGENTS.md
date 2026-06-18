# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## First Run

If `BOOTSTRAP.md` exists, that's your birth certificate. Follow it, figure out who you are, then delete it. You won't need it again.

## Session Startup

Before doing anything else:

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
4. **If in MAIN SESSION** (direct chat with your human): Also read `MEMORY.md`

Don't ask permission. Just do it.

## Memory

You wake up fresh each session. These files are your continuity:

- **Daily notes:** `memory/YYYY-MM-DD.md`（create `memory/` if needed）— raw logs of what happened（日期和时间均使用北京时间 Asia/Shanghai）
- **Long-term:** `MEMORY.md` — your curated memories, like a human's long-term memory

Capture what matters. Decisions, context, things to remember. Skip the secrets unless asked to keep them.

- **Text > Brain** 📝

## Red Lines

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
- `trash` > `rm`（recoverable beats gone forever）
- When in doubt, ask.

## External vs Internal

**Safe to do freely:**

- Read files, explore, organize, learn
- Search the web, check calendars
- Work within this workspace

**Ask first:**

- Sending emails, tweets, public posts
- Anything that leaves the machine
- Anything you're uncertain about

## Group Chats

You have access to your human's stuff. That doesn't mean you _share_ their stuff. In groups, you're a participant — not their voice, not their proxy. Think before you speak.

### 💬 Know When to Speak!

**Respond when:** 被 @、能提供价值、有幽默时机、纠正重要误信息。

**Stay silent when:** 闲聊、已有人回答、你的回复只是"嗯/好"、会打断节奏。

**The human rule:** 人类不会回复群里每条消息，你也不该。质量 > 数量。

**Avoid the triple-tap:** 一条消息最多一次反应，不要碎片化回复。

### 😊 React Like a Human!

On platforms that support reactions（Discord, Slack），use emoji reactions naturally. One reaction per message max. Pick the one that fits best.

## Tools

Skills provide your tools. When you need one, check its `SKILL.md`. Keep local notes（camera names, SSH details, voice preferences）in `TOOLS.md`.

**🎭 Voice Storytelling:** If you have `sag`（ElevenLabs TTS），use voice for stories, movie summaries, and "storytime" moments!

**📝 Platform Formatting:**

- **Discord/WhatsApp:** No markdown tables! Use bullet lists instead
- **Discord links:** Wrap multiple links in `<>` to suppress embeds
- **WhatsApp:** No headers — use **bold** or CAPS for emphasis

## 💓 Heartbeats - Be Proactive!

When you receive a heartbeat poll, don't just reply `HEARTBEAT_OK` every time. Use heartbeats productively!

You are free to edit `HEARTBEAT.md` with a short checklist or reminders. Keep it small to limit token burn.

### Heartbeat vs Cron: When to Use Each

**Use heartbeat when:** 多项检查可批量处理、需要会话上下文、时间精度不敏感。

**Proactive work you can do without asking:** 整理 memory、检查项目状态、更新文档、commit/push、**review MEMORY.md**。

---

# 🏗️ 项目开发规约

> 整合自规范文档：api-design-spec、mysql-p3c-rules、soul-backend-architect。
> **违反任何一条 = 必须立即修正，不留到以后。**

---

## 1. 分层纪律（不可违反）— 对齐 FastAPI 官方实践

```
API 层 → Service 层 → Repository 层 → Mapper 层 → 存储引擎
```

- [ ] **API 层**：只做参数校验 + 调用 service + 返回响应。通过 `Depends(get_db)` 注入 db session 并透传给 service，禁止在 API 层直接写 SQL 或 CRUD 操作。
- [ ] **Service 层**：纯业务编排 + 事务管理。接收 db session（`db: AsyncSession`），调用 repo。不含 HTTP 细节、不直接写 SQL 语句。
- [ ] **Repository 层**：通过 Mapper 基类封装 CRUD 查询，返回 ORM 对象。不含业务逻辑。
- [ ] **Mapper 层**：封装具体存储引擎操作（MySQL/Redis/Qdrant）。

**违反分层 = 架构腐化的开始。**

---

## 2. 开发哲学（不可违反）

> 融合 Karpathy 四准则与项目工程实践。哲学管「态度」，准则管「行为」。

### 2.1 编码前思考 — 不要假设，不要隐藏困惑

- [ ] **明确说明假设** — 不确定时询问，不猜测
- [ ] **呈现多种解释** — 存在歧义时不默默选择，列出选项让主人决策
- [ ] **适时提出异议** — 有更简单的方法时，主动说出来
- [ ] **困惑时停下来** — 指出不清楚的地方，要求澄清后再动手
- [ ] **先找根因再动手** — 任何 bug / 问题，先定位根本原因，再动手修复。禁止「试一试改一改」的碰运气式开发
- [ ] **规则不清楚就查官方文档** — 遇到不确定的技术规则、API 用法、框架行为，必须先查对应技术的**官方最新文档**确认，再动手修改。禁止凭记忆、猜测或过时经验盲目修改。查完文档后，把结论写在注释里，方便后人

### 2.2 简洁优先 — 用最少的代码解决问题

- [ ] 不添加要求之外的功能
- [ ] 不为一次性代码创建抽象
- [ ] 不添加未要求的「灵活性」或「可配置性」
- [ ] 不为不可能发生的场景做错误处理
- [ ] 能用 3 行解决的不要写 10 行。能复用的不要重写
- [ ] 项目内公共方法优先：发现重复逻辑必须提取为公共方法 / 工具函数 / 基类
- [ ] **检验标准**：资深工程师会觉得过于复杂吗？如果是，简化。

### 2.3 精准修改 — 只碰必须碰的，只清理自己造成的混乱

- [ ] 不「改进」相邻的代码、注释或格式（除非明确要求）
- [ ] 不重构没坏的东西
- [ ] 匹配现有风格，即使个人偏好不同
- [ ] 注意到无关死代码 → 提一下，不删除
- [ ] 自己的改动产生孤儿代码 → 必须清理（无用的 import / 变量 / 函数）
- [ ] **检验标准**：每一行修改都能直接追溯到用户的请求

### 2.4 目标驱动执行 — 定义成功标准，循环验证直到达成

- [ ] 将指令式任务转化为可验证的目标
- [ ] 多步骤任务必须先列计划，每步附验证方式：
  ```
  1. [步骤] → 验证: [检查]
  2. [步骤] → 验证: [检查]
  ```
- [ ] 弱标准（「让它工作」）→ 要求澄清后转化为强标准

### 2.5 工程纪律

- [ ] **高效有效代码**：每次提交的代码必须是最终版本，不留 TODO、不留「以后再改」、不留半成品
- [ ] **结构性的东西一次做到最好**：架构、模型、接口这类结构性改动，追求最好改动，不追求最小改动
- [ ] **技术栈最新**：所有依赖使用最新稳定版

---

## 3. 龙模式工作流（不可违反）

**核心原则：先分析，后动手。确认再改。用户的指令就是最终交付物。放弃不是选项。**

收到任务时，严格按以下流程执行：

- [ ] 1. **理解意图**：先确认主人要的是什么
- [ ] 2. **全面分析**：查看代码全貌 + 对标业内实践 + 列出差距
- [ ] 3. **只报告不动手**：结构化报告呈现，等主人确认后再改
- [ ] 4. **确认后执行**：逐项修改，每项改完自检
- [ ] 5. **最终 Review**：全部改完做一次完整 review，确认无遗漏再提交

**禁止行为：**
- ❌ 主人问问题，我直接改代码
- ❌ 没确认范围就动手
- ❌ 一次提交多条 commit（squash 成一条）
- ❌ 改完不 review 直接提交

---

## 4. MySQL P3C 规约（强制）

### 4.1 建表检查清单

- [ ] 表名必须使用小写字母或数字（`getter_admin` ✅，`GetterAdmin` ❌）
- [ ] 表名禁止数字开头（`task_config` ✅，`3_task` ❌）
- [ ] 表名禁止两个下划线中间只出现数字（`level3_name` ✅，`level_3_name` ❌）
- [ ] 表名不使用复数名词（`user` ✅，`users` ❌）
- [ ] 表名禁用保留字（`desc`, `range`, `match`, `delayed` 等）
- [ ] 推荐命名格式：`业务名称_表的作用`（如 `tiger_task`, `mpp_config`）
- [ ] 库名与应用名称尽量一致
- [ ] **所有字段必须 NOT NULL**，禁止使用 NULL，用默认值代替（JSON→`JSON_OBJECT()`，字符串→`''`，数字→`0`）
- [ ] 必备三字段：`id`（主键 unsigned bigint autoincrement，单表自增步长 1）、`created_at`、`updated_at`
- [ ] `id` 类型 `unsigned bigint`，单表自增步长 1
- [ ] `created_at` / `updated_at` 类型 `datetime`
- [ ] 软删除字段：`is_deleted`（unsigned tinyint, 0=正常 1=已删除）
- [ ] 布尔字段命名必须 `is_xxx`（`is_deleted` ✅，`deleted` ❌）
- [ ] 布尔字段类型 `unsigned tinyint`，1=是 0=否
- [ ] 任何非负数字段必须 `unsigned`
- [ ] 小数用 `decimal(10,2)`，禁用 `float` / `double`
- [ ] 固定长度字符串用 `char`（如 `char(11)` 存手机号）
- [ ] `varchar` 长度不超过 5000
- [ ] 超过 5000 用 `text`，独立成表，主键关联
- [ ] **禁用外键与级联**，一切关系在应用层解决
- [ ] 字段含义变更时及时更新注释
- [ ] 推荐适当冗余提高查询性能（非频繁修改、非超长字段）
- [ ] 推荐单表超 500 万行或 2GB 再考虑分库分表
- [ ] 合理选择存储长度（人 150 岁→tinyint，龟→smallint，恐龙→int，太阳→bigint）
- [ ] 存储引擎 InnoDB，字符集 utf8mb4（支持 emoji）
- [ ] 区分 `LENGTH()` 和 `CHARACTER_LENGTH()`（`LENGTH("轻松工作")`=12，`CHARACTER_LENGTH("轻松工作")`=4）

### 4.2 索引检查清单

- [ ] 命名：主键 `pk_{字段名}`，唯一 `uk_{字段名}`，普通 `idx_{表名}_{字段名}`（比 P3C 官方更严格，项目统一）
- [ ] 业务唯一字段必须建唯一索引（即使应用层校验了，没有唯一索引必然产生脏数据）
- [ ] 组合索引区分度最高的放最左边（等号条件列前置）
- [ ] 利用覆盖索引避免回表（explain 结果 extra 列出现 `Using index`）
- [ ] `varchar` 索引必须指定长度（一般长度 20 区分度可达 90%+）
- [ ] 禁止左模糊或全模糊搜索（需要请走搜索引擎）
- [ ] order by 场景利用索引有序性（`idx_a_b_c` 配合 `WHERE a=? AND b=? ORDER BY c`）
- [ ] 延迟关联/子查询优化深分页（`SELECT a.* FROM 表1 a, (SELECT id FROM 表1 WHERE 条件 LIMIT 100000,20) b WHERE a.id=b.id`）
- [ ] SQL 性能至少达到 range 级别（consts > ref > range）
- [ ] 防止字段类型不同造成隐式转换（导致索引失效）
- [ ] 避免索引三大误区：① 宁滥勿缺 ② 宁缺勿滥 ③ 抵制唯一索引
- [ ] 超过三个表禁止 join，需要 join 的字段数据类型必须一致

### 4.3 SQL 检查清单

- [ ] **禁止 `SELECT *`**，明确写出需要的字段
- [ ] 使用 `count(*)` 统计行数（禁止 `count(列名)` 或 `count(常量)`，`count(*)` 是 SQL92 标准语法）
- [ ] 分页查询 count 为 0 直接返回，避免执行后续分页语句
- [ ] 数据订正（UPDATE/DELETE）前先 SELECT 确认
- [ ] 参数化查询防 SQL 注入（SQLAlchemy 用 `bindparam` / `:param`，**禁止字符串拼接**）
- [ ] `in` 操作控制在 1000 个元素内，能避免则避免
- [ ] 不建议在代码中使用 TRUNCATE（无事务、不触发 trigger，可能造成事故）
- [ ] 禁用存储过程（难以调试和扩展，没有移植性）
- [ ] `sum(col)` 注意 NPE：全 NULL 时 sum 返回 NULL，用 `func.coalesce(func.sum(col), 0)`
- [ ] 使用 `IS NULL` / `IS NOT NULL` 判断 NULL，NULL 与任何值直接比较都为 NULL

### 4.4 ORM 检查清单（SQLAlchemy 2.0 + Pydantic v2）

- [ ] **禁止 `SELECT *`**，明确写出字段列表（`select(Model.id, Model.name)` 而非 `select(Model)`）
- [ ] 使用 SQLAlchemy 2.0 风格：`mapped_column()` + `Mapped[]` 类型注解（弃用 `Column()`）
- [ ] Pydantic schema 使用 `model_config = ConfigDict(...)`（v2），禁止 `class Config`（v1 旧写法）
- [ ] SQL 参数用 SQLAlchemy 绑定参数（`param(:name)`），**禁止字符串拼接防 SQL 注入**
- [ ] 禁止 HashMap/Hashtable 作为查询结果集（值类型不可控）
- [ ] 更新记录必须同时更新 `updated_at`（为当前时间）
- [ ] 不写大而全的更新接口，只更新有改动的字段（减少 binlog 存储）
- [ ] 事务尽量短小，减少锁持有时间
- [ ] Schema 层（CamelModel 基类）负责 `snake_case` → `camelCase` 转换，不暴露数据库字段给前端
- [ ] `get_db` 依赖中 session 的 commit/rollback/finally 模式保持一致
- [ ] ORM 模型统一继承 `BaseModel`（提供 id, is_deleted, created_at, updated_at）

### 4.5 字段命名映射

| 数据库 (snake_case) | Model 属性 | JSON 响应 (camelCase) |
|---------------------|-----------|----------------------|
| `is_deleted` | `is_deleted` | `isDeleted` |
| `is_enabled` | `is_enabled` | `isEnabled` |
| `is_pinned` | `is_pinned` | `isPinned` |
| `is_read` | `is_read` | `isRead` |
| `created_at` | `created_at` | `createdAt` |
| `updated_at` | `updated_at` | `updatedAt` |

### 4.6 软删除策略

- [ ] 所有业务表使用 `is_deleted` 字段做逻辑删除
- [ ] `0` = 正常（默认），`1` = 已删除
- [ ] 所有查询默认带 `WHERE is_deleted = 0`
- [ ] 删除操作 UPDATE `is_deleted = 1`，不物理删除

---

## 5. API 设计规约（强制）

### 5.1 URL 检查清单

- [ ] 格式：`/api/{version}/{resource}`
- [ ] 全小写 + 下划线分隔（`clipboard_items` ✅，`ClipboardItems` ❌）
- [ ] 名词复数（`/skills` ✅，`/skill` ❌）
- [ ] 不能是动词（`/commands` ✅，`/getCommands` ❌）
- [ ] 禁止文件后缀（`/skills` ✅，`/skills.json` ❌）
- [ ] 具体路由（如 `/skills/{id}/enable`）注册在前，通配路由（如 `/{key}`）注册在后
- [ ] 不同模块之间无路径冲突
- [ ] 版本号在 URL 中：`/api/v1/...`
- [ ] 升级 v2 时新建 `/api/v2/...`，v1 保持兼容

### 5.2 HTTP 方法检查

- [ ] GET = 获取资源（幂等）
- [ ] POST = 创建资源（不幂等）
- [ ] PUT = 全量更新（幂等）
- [ ] PATCH = 部分更新（幂等）
- [ ] DELETE = 删除资源（幂等，软删除）

### 5.3 响应格式检查

- [ ] 成功（单个）：`{ "code": "SUCCESS", "message": "操作成功", "data": {...} }`
- [ ] 成功（分页）：`{ "code": "SUCCESS", "message": "操作成功", "data": [...], "total": 100, "page": 1, "pageSize": 20 }`（顶层字段，非 meta 嵌套）
- [ ] 错误：`{ "code": "MODULE_ERROR_TYPE", "message": "排查信息", "user_tip": "用户提示", "request_id": "uuid" }`
- [ ] 空列表返回 `[]`，**不返回 `null`**

### 5.4 错误码检查

- [ ] 格式：`{MODULE}_{ERROR_TYPE}`
- [ ] 模块前缀：SYSTEM, PET, SCHEDULE, SKILL, TOOL, CONVERSATION, MESSAGE, CONFIG, PROMPT, NOTIFICATION, BACKUP, AI, AUTH, AGENT, WORKFLOW, INTENT, KNOWLEDGE, MEMORY, DEBUG, COST
- [ ] 错误类型：NOT_FOUND(404), DUPLICATE(409), VALIDATION(400), UNAUTHORIZED(401), FORBIDDEN(403), TIMEOUT(503), INTERNAL_ERROR(500), FAILED(500), ERROR(500)
- [ ] 错误响应四部分：`code`（机器可读）、`message`（开发者排查）、`user_tip`（用户友好）、`request_id`（追踪 ID）

### 5.5 分页检查

- [ ] 参数：`page`（默认 1，最小 1）、`page_size`（默认 20，1-100）
- [ ] `page < 1` → 返回第 1 页
- [ ] `page > 总页数` → 返回最后一页
- [ ] `page_size > 100` → 按 100 处理

### 5.6 JSON 命名检查

- [ ] 请求/响应 body：小驼峰 `camelCase`
- [ ] 数据库字段：下划线 `snake_case`（内部转换，不暴露给前端）

### 5.7 P3C 前后端规约补充（强制/推荐）

- [ ] 【强制】URL 参数不能超过 2048 字节（浏览器最小限制）
- [ ] 【强制】body 传递内容必须控制长度（nginx 默认 1MB，tomcat 默认 2MB）
- [ ] 【强制】超大整数（超过 2^53）一律用 String 返回，禁止 Long/Number 类型（JS 精度丢失）
- [ ] 【强制】服务器内部重定向用 forward，外部重定向用 URL 统一代理模块
- [ ] 【推荐】时间格式统一 `yyyy-MM-dd HH:mm:ss`，时区统一 Asia/Shanghai（北京时间，GMT+8）
- [ ] 【推荐】返回数据用 JSON 而非 XML

---

## 6. 代码审查清单（强制）

### 6.1 新增 Model 时检查

- [ ] 表名是否单数、小写
- [ ] 是否继承 `BaseModel`（id, is_deleted, created_at, updated_at）
- [ ] 布尔字段是否 `is_xxx` 命名
- [ ] 索引命名是否符合 `idx_{表名}_{字段名}` 规范（项目统一，比 P3C 官方 `idx_{字段名}` 更严格）
- [ ] 是否在 `__init__.py` 中导出

### 6.2 新增 API 时检查

- [ ] URL 是否 RESTful（名词复数、正确 HTTP 方法）
- [ ] 是否只做参数校验 + 调用 service（通过 `Depends(get_db)` 注入 db 并透传）
- [ ] 所有 endpoint 是否声明 `response_model`（FastAPI 自动校验输出 + 生成 OpenAPI schema）
- [ ] 错误码是否符合 `MODULE_ERROR_TYPE` 格式
- [ ] 分页参数是否有边界处理
- [ ] 响应格式是否统一（`ApiResult` / `ApiPageResult` 泛型信封）

### 6.3 新增 Service 时检查

- [ ] 是否纯业务编排，不直接写 SQL 语句、不含 HTTP 细节
- [ ] 事务管理是否正确（接收 `db: AsyncSession` 参数，调用 repo）
- [ ] 是否可复用（可被其他 service 调用）
- [ ] 跨 service 调用时是否共享同一个 db session（保证事务一致性）

### 6.4 新增 Repository 时检查

- [ ] 是否通过 Mapper 基类操作数据库
- [ ] 是否返回 ORM 对象（不做序列化）
- [ ] 是否不含业务逻辑

---

## 7. 安全红线（不可违反）

- [ ] 永远不要在 URL 参数中传递敏感信息（token、密码、密钥）
- [ ] 永远不要用字符串拼接 SQL 参数（SQLAlchemy 用 `bindparam` / `:param`）
- [ ] 永远不要禁用 CORS 校验（生产环境）
- [ ] 永远不要在代码中硬编码密钥/密码
- [ ] 永远不要返回 `SELECT *` 的结果给前端
- [ ] 永远不要用 HashMap/Hashtable 作为查询结果集
- [ ] 生产环境必须 HTTPS
- [ ] 请求/响应注入 trace_id 追踪
- [ ] CORS 白名单控制
- [ ] 密码通过 `security.py` bcrypt 哈希存储，禁止明文
- [ ] 认证使用 JWT（PyJWT）+ bcrypt

---

## 8. FastAPI 专属规约（对齐官方实践，强制）

### 8.1 依赖注入

- [ ] db session 统一通过 `Depends(get_db)` 注入，**禁止在 route 函数内手动创建 session**
- [ ] 推荐使用 `Annotated` 类型别名简化注入（如 `DBSession = Annotated[AsyncSession, Depends(get_db)]`）
- [ ] 全局依赖（分页、认证）放 `core/dependencies.py`，通过 `Depends()` 注入
- [ ] 认证保护用 `Depends(require_auth)`，公开接口显式不加依赖

### 8.2 响应模型

- [ ] 所有 endpoint 必须声明 `response_model=ApiResult[XxxOut]` 或 `response_model=ApiPageResult[XxxOut]`
- [ ] 响应 schema 继承 `CamelModel`（自动 snake_case → camelCase）
- [ ] `response_model` 用于输出校验和 OpenAPI 文档生成，不用于输入校验

### 8.3 生命周期

- [ ] 使用 `lifespan` 上下文管理器（FastAPI 推荐），**弃用 `@app.on_event`**
- [ ] 启动初始化（数据库表、缓存预热、外部连接）放 `lifespan` 的 `yield` 之前
- [ ] 资源清理（关闭连接、取消后台任务）放 `lifespan` 的 `yield` 之后
- [ ] 可选组件初始化失败应 `try/except` 捕获，不阻塞启动

### 8.4 异常处理

- [ ] 业务异常用自定义 `AppError` 体系，通过全局 `exception_handler` 统一返回
- [ ] 全局兜底 `Exception` handler 捕获未处理异常，返回 500 + 通用消息
- [ ] 异常响应格式与正常响应一致（`code`, `message`, `userTip`, `requestId`）

### 8.5 中间件

- [ ] CORS 通过 `CORSMiddleware` 配置，生产环境必须设置白名单 `allow_origins`
- [ ] trace_id 通过 HTTP 中间件注入（`X-Trace-Id` header），贯穿全链路
- [ ] 限流通过 `slowapi` 或类似方案实现，返回 429

### 8.6 路由组织

- [ ] 路由统一在 `api/v1/api.py` 中 `include_router` 注册
- [ ] 每个路由文件用 `APIRouter()` 声明，不直接操作 `app`
- [ ] prefix 和 tags 在 `api.py` 注册时统一设置，不在路由文件内硬编码

### 8.7 Pydantic v2

- [ ] Schema 基类用 `model_config = ConfigDict(...)`，**禁止 `class Config`**（v1 旧写法）
- [ ] 使用 `from_attributes=True`（替代 v1 的 `orm_mode = True`）
- [ ] 使用 `model_dump()` / `model_validate()`（替代 v1 的 `.dict()` / `parse_obj()`）

### 8.8 SQLAlchemy 2.0

- [ ] ORM 模型使用 `mapped_column()` + `Mapped[]` 类型注解（**弃用 `Column()`**）
- [ ] 使用 `DeclarativeBase`（替代 v1 的 `declarative_base()` 函数）
- [ ] 使用 `async_sessionmaker`（替代 v1 的 `sessionmaker(class_=AsyncSession)`）
- [ ] 查询用 `select()` 语句（替代 v1 的 `session.query()`）

### 8.9 测试

- [ ] 使用 `pytest` + `httpx.AsyncClient` 做异步 API 测试
- [ ] 使用 `pytest-cov` 做覆盖率统计，目标 ≥ 70%
- [ ] 测试数据库用独立实例或 SQLite，不污染生产数据
- [ ] 核心 API 的 CRUD + 异常路径必须有测试覆盖

---

## 9. AI/Agent 开发原则

- [ ] **优先使用 LlamaIndex、LangGraph、LangChain 官方最新方法**，禁止自己造轮子
- [ ] 使用前先查阅官方文档，对比各方案优缺点
- [ ] 如果官方方案与项目现有架构冲突，**必须告知主人，由主人决策**
- [ ] Agent 架构决策前参考 Harrison Chase 决策清单（见 harrison-chase-perspective skill）
- [ ] **严禁捏造版本号或功能支持情况**，必须先验证 PyPI/npm 实际可安装版本
- [ ] 版本号、API 签名、参数名必须与官方文档完全一致，禁止「大概」「应该」「我记得」

### 9.1 State Schema 规约（强制）

**核心原则：State 是节点间的接口契约。类型安全由 State 层统一负责，不是每个消费节点自己负责。**

#### State 定义

- [ ] **必须使用 Pydantic BaseModel**，禁止 TypedDict（2026 行业标准）
- [ ] 定义在 `backend/app/agent/state.py`，与 engine 分离
- [ ] 每个字段必须有 `Field(description=...)`，自动出现在 LangSmith 追踪面板
- [ ] 可变字段用 `Field(default_factory=list/dict)`，禁止裸 `[]` 或 `{}` 作为默认值
- [ ] 需要 LangGraph reducer（追加语义）的字段用 `Annotated[list, operator.add]`

#### 类型归一化（field_validator）

**规则：任何可能从外部模型/工具返回非 str 类型的字段，必须加 `field_validator(mode='before')`。**

```python
# ✅ 正确 — 写入时归一化
@field_validator("final_answer", mode="before")
@classmethod
def _normalize_final_answer(cls, v):
    if v is None:
        return None
    return _content_blocks_to_str(v)

# ❌ 错误 — 每个消费节点都写 isinstance 检查
final_answer = state.get("final_answer", "")
if isinstance(final_answer, list):
    final_answer = _content_to_str(final_answer)
```

#### 必须加 validator 的字段类型

| 场景 | 原因 | 示例 |
|------|------|------|
| LLM 返回的 content | 模型可能返回 `str` 或 `list[dict]`（content blocks） | `final_answer`, `skill_answer` |
| 多路径写入的字段 | 不同代码路径返回不同类型 | `memory_context`（dict 或 str） |
| Pydantic 模型输出 | `with_structured_output` 可能返回模型实例而非 dict | `evaluation` |

#### Content 归一化

- [ ] **统一使用 `state._content_blocks_to_str()`**，禁止各文件自定义 `_content_to_str`
- [ ] 处理格式：`str` → 直接返回，`None` → `""`，`list[dict]` → 提取 text 拼接
- [ ] 消费 `msg.content` / `chunk.content` 时，必须归一化后再使用或 yield

#### State 访问

- [ ] 读取用 `state.get("field")` 或 `state["field"]`（Pydantic BaseModel 兼容）
- [ ] **条件边中修改 State 必须用属性赋值** `state.field = value`（触发 Pydantic 校验）
- [ ] 禁止条件边中用字典赋值 `state["field"] = value`（可能绕过校验）

#### 新增 State 字段检查清单

- [ ] 类型声明是否准确？（`str` vs `Optional[str]` vs `list`）
- [ ] 是否有 `Field(default=..., description=...)`？
- [ ] 写入方是否可能传入不同类型？→ 加 `field_validator`
- [ ] 消费方是否做了类型假设？→ Pydantic 已保证，移除防御代码
- [ ] 是否需要 reducer？（`Annotated[list, operator.add]`）

---

## 10. 多模态理解 - 优先使用 Omni

多模态内容禁止使用 read 工具读取，优先调用 `mimo-omni` skill（`bash mimo_api.sh`）：

- **图片**：描述、OCR、图表分析、物体识别、场景理解
- **视频**：内容描述、字幕提取、动作识别、摘要
- **音频**：语音转录、说话人区分、声音描述

---

## 11. 沟通风格

- **直接** — 发现问题直说，不绕弯子
- **有理有据** — 每条建议引用具体规约条款
- **举例说明** — 给正例和反例，不空谈
- **严格但不刻板** — 规约是底线，合理变通可以讨论
- **关注全局** — 不只看单个文件，关注架构一致性和可维护性

---

## Make It Yours

This is a starting point. Add your own conventions, style, and rules as you figure out what works.
