"""用户模型"""
from sqlalchemy import Column, String, SmallInteger
from app.models.base import BaseModel


class User(BaseModel):
    """用户账号表"""
    __tablename__ = "t_user_account"

    username = Column(String(64), nullable=False, unique=True, comment="用户名（登录账号）")
    password_hash = Column(String(128), nullable=False, comment="密码哈希（bcrypt）")
    nickname = Column(String(64), nullable=False, default="", comment="昵称")
    avatar_url = Column(String(512), nullable=False, default="", comment="头像 URL")
    user_role = Column(SmallInteger, nullable=False, default=0, comment="角色: 0=普通用户 1=管理员")
    is_enabled = Column(SmallInteger, nullable=False, default=1, comment="是否启用: 1=是 0=否")
