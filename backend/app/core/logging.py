"""日志配置 - P3C 规范"""
import logging
import os
import sys
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
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

    # 控制台日志处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(TraceFilter())
    console_handler.addFilter(SensitiveFilter())

    # 文件日志处理器（按日期轮转）
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "log")
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建按日期轮转的文件处理器，每天创建新的日志文件
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,  # 保留30天的日志
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(TraceFilter())
    file_handler.addFilter(SensitiveFilter())
    
    # 设置日志文件后缀为日期格式
    file_handler.suffix = "%Y-%m-%d"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取模块日志器"""
    return logging.getLogger(name)
