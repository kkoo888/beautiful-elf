# Beautiful-Elf API 设计规范

> 基于《阿里巴巴 Java 开发手册》前后端规约，结合项目实际制定。

---

## 1. URL 路径规范

### 1.1 基本格式

```
/api/{version}/{resource}
/api/{version}/{resource}/{id}
/api/{version}/{resource}/{id}/{action}
```

### 1.2 命名规则

| 规则 | 正例 | 反例 |
|------|------|------|
| 全小写 | `clipboard_items` | `ClipboardItems` |
| 下划线分隔 | `ai_feedback` | `ai-feedback` |
| 名词复数 | `conversations` | `conversation` |
| 不能是动词 | `commands` | `getCommands` |
| 禁止文件后缀 | `/api/v1/skills` | `/api/v1/skills.json` |

### 1.3 路由注册顺序

1. 具体路由（如 `/skills/{id}/enable`）注册在前
2. 通配路由（如 `/{key}`）注册在后
3. 不同模块之间无路径冲突

---

## 2. HTTP 方法

| 方法 | 语义 | 幂等 | 示例 |
|------|------|------|------|
| GET | 获取资源 | ✅ | `GET /api/v1/skills` |
| POST | 创建资源 | ❌ | `POST /api/v1/skills` |
| PUT | 全量更新 | ✅ | `PUT /api/v1/skills/1` |
| PATCH | 部分更新 | ✅ | `PATCH /api/v1/skills/1/enable` |
| DELETE | 删除资源 | ✅ | `DELETE /api/v1/skills/1` |

---

## 3. 统一响应格式

### 3.1 成功响应

**单个资源：**
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": { ... }
}
```

**列表（无分页）：**
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": [ ... ]
}
```

**列表（带分页）：**
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": [ ... ],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

**空列表：** 返回 `[]`，不返回 `null`。

### 3.2 错误响应

```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "记录不存在",
  "user_tip": "请检查请求的资源 ID 是否正确",
  "request_id": "5afc3400-808d-4144-a565-63aeda2b235d"
}
```

四部分：
- `code`：错误码（机器可读，前端用于分支处理）
- `message`：开发排查信息（给开发者看）
- `user_tip`：用户友好提示（给终端用户看）
- `request_id`：请求追踪 ID

---

## 4. 错误码规范

### 4.1 格式

```
{MODULE}_{ERROR_TYPE}
```

### 4.2 模块前缀

| 前缀 | 模块 |
|------|------|
| `SYSTEM` | 系统级（数据库、通用） |
| `PET` | 宠物系统 |
| `SCHEDULE` | 日程系统 |
| `SKILL` | 技能系统 |
| `TOOL` | 工具系统 |
| `CONVERSATION` | 会话系统 |
| `MESSAGE` | 消息系统 |
| `CONFIG` | 配置系统 |
| `PROMPT` | 提示词系统 |
| `NOTIFICATION` | 通知系统 |
| `BACKUP` | 备份系统 |
| `AI` | AI 相关 |
| `AUTH` | 认证授权 |

### 4.3 错误类型

| 类型 | HTTP 状态码 | 说明 |
|------|------------|------|
| `NOT_FOUND` | 404 | 资源不存在 |
| `DUPLICATE` | 409 | 重复创建 |
| `VALIDATION` | 400 | 参数校验失败 |
| `UNAUTHORIZED` | 401 | 未认证 |
| `FORBIDDEN` | 403 | 无权限 |
| `TIMEOUT` | 503 | 超时 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

### 4.4 示例

| code | HTTP 状态码 | message | user_tip |
|------|------------|---------|----------|
| `PET_NOT_FOUND` | 404 | 宠物记录不存在 | 请先创建宠物 |
| `SKILL_DUPLICATE` | 409 | 技能已存在 | 该技能已安装，请勿重复添加 |
| `SYSTEM_VALIDATION` | 400 | 参数校验失败 | 请检查输入参数 |
| `CONFIG_NOT_FOUND` | 404 | 配置项不存在 | 请检查配置键名 |
| `AI_TIMEOUT` | 503 | AI 模型响应超时 | 请稍后重试 |

---

## 5. 分页规范

### 5.1 请求参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（最小 1） |
| `page_size` | int | 20 | 每页数量（1-100） |

### 5.2 边界处理

- `page < 1` → 返回第 1 页
- `page > 总页数` → 返回最后一页
- `page_size > 100` → 按 100 处理

### 5.3 响应格式

```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": [],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 6. JSON 字段命名

- 响应体 key：**小驼峰** `camelCase`
- 请求体 key：**小驼峰** `camelCase`
- 数据库字段：**下划线** `snake_case`（内部转换，不暴露给前端）

---

## 7. 路由映射表

| 资源 | URL 前缀 | 说明 |
|------|----------|------|
| 会话 | `/api/v1/conversations` | CRUD + 子资源 |
| 消息 | `/api/v1/conversations/{id}/messages` | 会话下的消息 |
| 日程 | `/api/v1/schedules` | CRUD |
| 剪贴板 | `/api/v1/clipboard_items` | CRUD + pin 操作 |
| 代码片段 | `/api/v1/snippets` | CRUD + use 统计 |
| 命令 | `/api/v1/commands` | CRUD + use 统计 |
| 宠物 | `/api/v1/pets` | CRUD + 互动子资源 |
| 通知 | `/api/v1/notifications` | CRUD + 已读操作 |
| 技能 | `/api/v1/skills` | CRUD + 启用/禁用 |
| 工具 | `/api/v1/tools` | CRUD + 启用/禁用 |
| 配置 | `/api/v1/configs` | key-value CRUD |
| 灵魂配置 | `/api/v1/soul_configs` | CRUD + active |
| 提示词 | `/api/v1/prompts` | CRUD + 版本管理 |
| 性能 | `/api/v1/performance` | 监控数据 |
| 备份 | `/api/v1/backups` | CRUD |
| AI 反馈 | `/api/v1/ai_feedback` | CRUD + 统计 |
| 操作日志 | `/api/v1/action_logs` | 查询 + 清理 |
| 命令统计 | `/api/v1/command_usage` | 记录 + 排行 |
| 健康检查 | `/api/v1/health` | 系统状态 |
| 认证 | `/api/v1/auth` | 登录/注册（预留） |

---

## 8. 版本管理

- 当前版本：`v1`
- 版本号在 URL 路径中：`/api/v1/...`
- 升级 v2 时新建 `/api/v2/...`，v1 保持兼容

---

## 9. 安全

- 生产环境必须 HTTPS
- 敏感信息禁止出现在 URL 参数中
- CORS 白名单控制
- 请求/响应 trace_id 注入
