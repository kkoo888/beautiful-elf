"""全局依赖 - 分页、认证等 FastAPI 依赖项"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


# ==================== 分页依赖 ====================
@dataclass
class PaginationParams:
    """分页参数"""
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(page: int = 1, page_size: int = 20) -> PaginationParams:
    """分页参数依赖"""
    page = max(1, page)
    page_size = max(1, min(100, page_size))  # 限制 1-100
    return PaginationParams(page=page, page_size=page_size)


# ==================== 认证依赖 ====================
@dataclass
class CurrentUser:
    """当前认证用户"""
    user_id: int
    username: str


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[CurrentUser]:
    """
    获取当前认证用户
    - 有 token → 校验并返回用户
    - 无 token → 返回 None（允许匿名访问部分接口）
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    username = payload.get("username", "")
    if user_id is None:
        return None

    return CurrentUser(user_id=int(user_id), username=username)


async def require_auth(
    user: Optional[CurrentUser] = Depends(get_current_user),
) -> CurrentUser:
    """强制要求认证，未登录抛 401"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或 token 已过期",
        )
    return user
