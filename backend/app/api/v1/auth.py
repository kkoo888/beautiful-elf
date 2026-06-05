"""认证 API — 登录 / 注册 / 个人信息"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.schemas.auth import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    UpdateProfileRequest, UserInfoOut, LoginResponse,
)
from app.schemas.response import ApiResult
from app.services.auth_service import auth_service

router = APIRouter()


# ─── 依赖：从 Header 提取当前用户 ─────────────────

def _get_current_user_id(token_data: dict = Depends(lambda: None)) -> int:
    """从 Authorization header 解析 user_id（简单版，后续可换 OAuth2）"""
    # 这里先用 query 方式，前端登录后调用接口时带上 token
    raise NotImplementedError("请通过 /login 获取 token 后在请求头携带")


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


# ─── 需要登录的接口 ──────────────────────────────

@router.get("/me", response_model=ApiResult[UserInfoOut])
async def get_current_user(
    authorization: str = "",
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户信息"""
    user_id = _extract_user_id(authorization)
    user = await auth_service.get_current_user(db, user_id)
    return ApiResult(data=user)


@router.post("/change-password", response_model=ApiResult)
async def change_password(
    data: ChangePasswordRequest,
    authorization: str = "",
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    user_id = _extract_user_id(authorization)
    await auth_service.change_password(db, user_id, data)
    return ApiResult(message="密码修改成功")


@router.put("/profile", response_model=ApiResult[UserInfoOut])
async def update_profile(
    data: UpdateProfileRequest,
    authorization: str = "",
    db: AsyncSession = Depends(get_db),
):
    """更新个人信息"""
    user_id = _extract_user_id(authorization)
    user = await auth_service.update_profile(db, user_id, data)
    return ApiResult(data=user, message="更新成功")


# ─── 工具函数 ─────────────────────────────────────

def _extract_user_id(authorization: str) -> int:
    """从 Authorization: Bearer <token> 提取 user_id"""
    from fastapi import HTTPException

    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")

    # 支持 "Bearer <token>" 或直接传 token
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")

    user_id = payload.get("user_id") or payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="token 中无用户信息")

    return int(user_id)
