"""应用配置 - 通过环境变量读取数据库连接信息"""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


def _detect_project_root() -> str:
    """自动检测项目根目录

    策略（OpenClaw + Claude Code 混合模式）：
    1. 从当前文件向上查找项目标记文件（docker-compose.yml, .git, backend/）
    2. 找到即返回，找不到回退到 CWD
    """
    # 从 backend/app/core/config.py 向上最多查 5 层
    current = Path(__file__).resolve().parent
    markers = {"docker-compose.yml", "docker-compose.yaml", ".git"}
    for _ in range(5):
        # 检查是否有项目标记
        if any((current / m).exists() for m in markers):
            # 确认是项目根目录（有 backend/ 子目录）
            if (current / "backend").is_dir():
                return str(current)
        current = current.parent
    # 回退：如果从 backend/ 启动，取父目录
    cwd = Path.cwd()
    if (cwd / "backend").is_dir() and (cwd / "docker-compose.yml").exists():
        return str(cwd)
    if cwd.name == "backend" and cwd.parent != cwd:
        return str(cwd.parent)
    return str(cwd)


class Settings(BaseSettings):
    """应用配置，所有敏感配置通过环境变量传入"""

    # FastAPI
    APP_NAME: str = "Beautiful-Elf"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "beautiful_elf"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    @property
    def QDRANT_URL(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # Ollama
    OLLAMA_HOST: str = "http://localhost:11434"

    # SearXNG
    SEARXNG_URL: str = ""

    # MCP Server
    MCP_SERVER_HOST: str = "0.0.0.0"
    MCP_SERVER_PORT: int = 6880

    # Workspace — 默认自动检测项目根目录（backend/ 的父目录）
    # 显式设置 WORKSPACE_DIR 可覆盖
    WORKSPACE_DIR: str = ""

    @property
    def RESOLVED_WORKSPACE(self) -> str:
        """解析后的工作目录：显式配置 > 自动检测"""
        if self.WORKSPACE_DIR:
            return str(Path(self.WORKSPACE_DIR).resolve())
        return _detect_project_root()

    @property
    def WORKSPACE(self) -> Path:
        """解析后的工作目录（Path 对象）"""
        return Path(self.RESOLVED_WORKSPACE)

    # JWT — 必须在 .env 中设置，禁止空值和默认值
    JWT_SECRET_KEY: str = ""
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 默认 24 小时

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "file://",
    ]

    # Connection pool
    MYSQL_POOL_SIZE: int = 10
    MYSQL_MAX_OVERFLOW: int = 20
    MYSQL_POOL_TIMEOUT: int = 30
    MYSQL_POOL_RECYCLE: int = 3600

    REDIS_MAX_CONNECTIONS: int = 20

    # WebSocket
    WS_QUEUE_MAXSIZE: int = 2000
    WS_HEARTBEAT_INTERVAL: int = 30  # 秒
    WS_IDLE_TIMEOUT: int = 1800  # 30 分钟

    @property
    def MYSQL_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def SYNC_MYSQL_URL(self) -> str:
        """同步 URL，用于 Alembic 迁移"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
