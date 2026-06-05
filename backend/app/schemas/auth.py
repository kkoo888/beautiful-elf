"""认证相关 Schema"""
from typing import Optional
from pydantic import Field
from app.schemas.base import CamelModel


class LoginRequest(CamelModel):
    """登录请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=4, max_length=128, description="密码")


class RegisterRequest(CamelModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=4, max_length=128, description="密码")
    nickname: str = Field(default="", max_length=64, description="昵称")


class ChangePasswordRequest(CamelModel):
    """修改密码"""
    old_password: str = Field(..., max_length=128, description="旧密码")
    new_password: str = Field(..., min_length=4, max_length=128, description="新密码")


class UpdateProfileRequest(CamelModel):
    """更新个人信息"""
    nickname: Optional[str] = Field(default=None, max_length=64, description="昵称")
    avatar: Optional[str] = Field(default=None, max_length=512, description="头像 URL")


class UserInfoOut(CamelModel):
    """用户信息输出"""
    id: int
    username: str
    nickname: str
    avatar: str
    role: str
    status: int


class LoginResponse(CamelModel):
    """登录响应"""
    token: str
    user: UserInfoOut
