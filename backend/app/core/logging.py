"""日志配置 - P3C 规范"""
import logging
import sys
from contextvars import ContextVar
from app.core.config import get_settings

# 请求链路 ID 上下文
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


class SensitiveFilter(logging.Filter):
    """敏感数据脱敏过滤器"""
    SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization"}

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "msg") and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for key in self.SENSITIVE_KEYS:
                if key in msg_lower and "=" in record.msg:
                    # 简单脱敏：key=xxx 中间用 *** 替换
                    parts = record.msg.split("=")
                    if len(parts) > 1:
                        record.msg = f"{parts[0]}=***"
        return True


class TraceFilter(logging.Filter):
    """注入 trace_id 到日志记录"""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get("")
        record.user_id = user_id_var.get("")
        return True


def setup_logging():
    """初始化日志系统"""
    settings = get_settings()
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    formatter = logging.Formatter(
        fmt=(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
            '"module":"%(module)s","trace_id":"%(trace_id)s",'
            '"user_id":"%(user_id)s","message":"%(message)s"}'
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(TraceFilter())
    handler.addFilter(SensitiveFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # 降低第三方库日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取模块日志器"""
    return logging.getLogger(name)
