"""认证 API — 登录 / 注册 / 个人信息"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import AuthUnauthorizedError
from app.schemas.auth import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    UpdateProfileRequest, UserInfoOut, LoginResponse,
)
from app.schemas.response import ApiResult
from app.services.auth_service import auth_service

router = APIRouter()


# ─── 全局依赖：从 Authorization Header 提取 user_id ──

async def get_current_user_id(
    authorization: Optional[str] = Header(default=None),
) -> int:
    """从 Authorization: Bearer <token> 提取 user_id，作为 FastAPI 依赖使用"""
    if not authorization:
        raise AuthUnauthorizedError(message="未携带 token", user_tip="请先登录")

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    payload = decode_access_token(token)
    if not payload:
        raise AuthUnauthorizedError(message="token 无效或已过期", user_tip="请重新登录")

    user_id = payload.get("user_id") or payload.get("sub")
    if user_id is None:
        raise AuthUnauthorizedError(message="token 中无用户信息", user_tip="请重新登录")

    return int(user_id)


# ─── 公开接口（无需登录）─────────────────────────

@router.post("/register", response_model=ApiResult[UserInfoOut])
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户"""
    user = await auth_service.register(db, data)
    return ApiResult(data=user, message="注册成功")


@router.post("/login", response_model=ApiResult[LoginResponse])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """登录，返回 JWT token + 用户信息"""
    result = await auth_service.login(db, data)
    return ApiResult(data=result, message="登录成功")


# ─── 需要登录的接口（通过 Depends 注入 user_id）────

@router.get("/me", response_model=ApiResult[UserInfoOut])
async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户信息"""
    user = await auth_service.get_current_user(db, user_id)
    return ApiResult(data=user)


@router.post("/change-password", response_model=ApiResult)
async def change_password(
    data: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    await auth_service.change_password(db, user_id, data)
    return ApiResult(message="密码修改成功")


@router.put("/profile", response_model=ApiResult[UserInfoOut])
async def update_profile(
    data: UpdateProfileRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新个人信息"""
    user = await auth_service.update_profile(db, user_id, data)
    return ApiResult(data=user, message="更新成功")
