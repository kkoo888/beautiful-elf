"""用户模型"""
from sqlalchemy import Column, String, SmallInteger
from app.models.base import BaseModel


class User(BaseModel):
    """用户表"""
    __tablename__ = "user"

    username = Column(String(64), nullable=False, unique=True, comment="用户名")
    password_hash = Column(String(128), nullable=False, comment="密码哈希（bcrypt）")
    nickname = Column(String(64), nullable=False, default="", comment="昵称")
    avatar = Column(String(512), nullable=False, default="", comment="头像 URL")
    user_role = Column(String(32), nullable=False, default="user", comment="角色: admin / user")
    is_enabled = Column(SmallInteger, nullable=False, default=1, comment="是否启用: 1=是 0=否")
