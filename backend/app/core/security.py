"""安全模块 - JWT 认证 + 密码哈希"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# JWT 算法，固定不变
JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """获取 JWT 密钥，未配置时启动报错"""
    secret = get_settings().JWT_SECRET_KEY
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY 未设置！请在 .env 中配置: "
            "python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    return secret


def hash_password(password: str) -> str:
    """密码哈希（bcrypt）"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """解码 JWT token，失败返回 None 并记录日志"""
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("JWT 验证失败: token 已过期")
        return None
    except jwt.InvalidSignatureError:
        logger.error("JWT 验证失败: 签名不匹配（JWT_SECRET_KEY 可能已更换）")
        return None
    except jwt.DecodeError as e:
        logger.warning(f"JWT 验证失败: 解码错误 — {e}")
        return None
    except jwt.PyJWTError as e:
        logger.warning(f"JWT 验证失败: {type(e).__name__} — {e}")
        return None
