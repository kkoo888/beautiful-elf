# Beautiful-Elf 后端运行指南

## 一、环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 推荐 3.12 |
| MySQL | 9.5+ | 或 MariaDB 11+ |
| Redis | 8.0+ | 缓存 + 消息队列 |
| Qdrant | 最新 | 向量数据库 |
| Ollama | 最新 | 本地大模型（可选） |

## 二、快速启动

### 1. 克隆代码

```bash
git clone git@github.com:kkoo888/beautiful-elf.git
cd beautiful-elf
git checkout dev
```

### 2. 启动数据库（Docker Compose）

在项目根目录创建 `docker-compose.yml`：

```yaml
version: "3.8"
services:
  mysql:
    image: mysql:9.5
    container_name: beautiful-elf-mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: root123
      MYSQL_DATABASE: beautiful_elf
      MYSQL_CHARSET: utf8mb4
    volumes:
      - mysql_data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis:
    image: redis:8.0
    container_name: beautiful-elf-redis
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    container_name: beautiful-elf-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  mysql_data:
  qdrant_data:
```

启动：
```bash
docker compose up -d
```

### 3. 安装 Python 依赖

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `backend/.env` 文件：

```env
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123
MYSQL_DATABASE=beautiful_elf

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Ollama（可选）
OLLAMA_HOST=http://localhost:11434

# 调试模式
DEBUG=true
```

### 5. 初始化数据库表

```bash
cd backend

# 方式一：自动建表（开发阶段，启动时自动创建）
python3 main.py

# 方式二：Alembic 迁移（生产推荐）
alembic revision --autogenerate -m "init tables"
alembic upgrade head
```

### 6. 启动后端服务

```bash
cd backend

# 开发模式（热更新）
python3 main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. 验证服务

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 就绪检查（MySQL + Redis + Qdrant 全部连通才返回 ok）
curl http://localhost:8000/api/v1/ready

# 依赖详情
curl http://localhost:8000/api/v1/deps

# API 文档（浏览器打开）
open http://localhost:8000/docs
```

## 三、连接远程数据库

如果数据库在远程服务器，只需修改 `.env`：

```env
MYSQL_HOST=你的服务器IP
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=beautiful_elf

REDIS_HOST=你的服务器IP
REDIS_PORT=6379
REDIS_PASSWORD=

QDRANT_HOST=你的服务器IP
QDRANT_PORT=6333
```

## 四、常见问题

### Q: MySQL 连接报错 "Access denied"
检查 MySQL 用户是否有远程访问权限：
```sql
-- 在 MySQL 中执行
CREATE USER 'root'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON beautiful_elf.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

### Q: Redis 连接超时
检查 Redis 是否允许远程连接：
```bash
# redis.conf 中修改
bind 0.0.0.0
# 如果设置了密码，.env 中填写 REDIS_PASSWORD
```

### Q: Qdrant 连不上
检查防火墙是否放行 6333 端口。

### Q: 启动报错 "Table doesn't exist"
确保 MySQL 中已创建 `beautiful_elf` 数据库：
```sql
CREATE DATABASE IF NOT EXISTS beautiful_elf DEFAULT CHARSET utf8mb4;
```

## 五、API 路由总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/health | 存活检查 |
| GET | /api/v1/ready | 就绪检查 |
| GET | /api/v1/deps | 依赖详情 |
| CRUD | /api/v1/config | 配置管理 |
| CRUD | /api/v1/schedules | 日程管理 |
| CRUD | /api/v1/clipboard-items | 剪贴板 |
| CRUD | /api/v1/snippets | 代码片段 |
| GET/PUT | /api/v1/pet-attributes | 宠物属性 |
| POST | /api/v1/pet-attributes/interact | 宠物互动 |
| CRUD | /api/v1/commands | 命令面板 |
| CRUD | /api/v1/conversations | 会话管理 |
| CRUD | /api/v1/messages | 消息记录 |
| CRUD | /api/v1/notifications | 通知系统 |
| GET | /api/v1/performance/current | 当前性能 |
| GET | /api/v1/performance/metrics | 性能历史 |
| CRUD | /api/v1/soul-configs | 人格配置 |

完整 API 文档：启动后访问 http://localhost:8000/docs
