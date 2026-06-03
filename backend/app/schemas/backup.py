"""备份管理 Schema"""
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class BackupCreate(CamelModel):
    backup_type: int = Field(..., ge=0, le=2, description="备份类型: 0=MySQL, 1=Redis, 2=全量")
    file_path: str = Field(..., max_length=512, description="备份文件路径")
    file_size: int = Field(default=0, ge=0, description="文件大小 (字节)")
    status: int = Field(default=0, ge=0, le=2, description="状态: 0=进行中, 1=成功, 2=失败")
    error_message: str = Field(default="", max_length=1024, description="失败原因")


class BackupStatusUpdate(CamelModel):
    status: int = Field(..., ge=1, le=2, description="状态: 1=成功, 2=失败")
    error_message: str = Field(default="", max_length=1024, description="失败原因")
    file_size: int = Field(default=0, ge=0, description="文件大小 (字节)")


class BackupOut(CamelModel):
    id: int
    backup_type: int
    file_path: str
    file_size: int
    status: int
    error_message: str
    created_at: datetime
    updated_at: datetime
