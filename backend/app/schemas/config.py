"""配置管理 Schema"""
from typing import Optional
from pydantic import BaseModel


class SettingCreate(BaseModel):
    """创建配置"""
    settings_key: str
    key_value: str
    description: str = ""
    restart_required: int = 0


class SettingUpdate(BaseModel):
    """更新配置"""
    key_value: Optional[str] = None
    description: Optional[str] = None
    restart_required: Optional[int] = None


class SettingOut(BaseModel):
    """配置输出"""
    id: int
    settings_key: str
    key_value: str
    description: str
    restart_required: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
