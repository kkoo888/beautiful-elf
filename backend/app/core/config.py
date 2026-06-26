"""应用配置 - 通过环境变量读取数据库连接信息"""
from pydantic_settings import BaseSettings
from functools import lru_cache


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

    # Workspace
    WORKSPACE_DIR: str = "./workspace"

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
